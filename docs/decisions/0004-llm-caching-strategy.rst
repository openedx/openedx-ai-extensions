0004 LLM Caching Strategy
#########################

Status
******
**Proposed**

Context
*******

As the number of AI-powered workflows in the platform grows, so does the volume and
cost of LLM API calls. Repeated or structurally similar requests — such as summarizing
the same content, generating questions for a shared lesson, or running system-prompted
workflows — represent an opportunity for caching to reduce both latency and API spend.

Two distinct caching mechanisms are available through LiteLLM, and they operate at
different layers:

1. **LiteLLM Proxy Response Caching** — LiteLLM intercepts requests and returns a
   previously stored full response when an identical request is detected (same model,
   messages, temperature, etc.). This is a client-side cache from the LLM provider's
   perspective. Supported backends include: in-memory, disk, Redis, S3, GCS, and
   semantic (Qdrant/Redis). Cache behaviour can be controlled per-request using
   ``ttl``, ``s-maxage``, ``no-cache``, ``no-store``, and ``namespace`` parameters.

   **Critical limitation**: This mechanism does **not** support the OpenAI ``/responses``
   API endpoint (``responses`` call type). It only works for ``/chat/completions``,
   ``/completions``, ``/embeddings``, and ``/audio/transcriptions``. Any workflow that
   relies on the Responses API cannot benefit from this cache layer.

2. **Provider-Side Prompt Caching** — The LLM provider (OpenAI, Anthropic, Bedrock,
   Deepseek) caches the KV-tensor computation for the prompt prefix. The API is still
   called, but token processing cost and latency are reduced for cache hits. LiteLLM
   transparently surfaces cache usage through a normalised ``prompt_tokens_details.cached_tokens``
   field in the response.

   Provider behaviour differs:

   * **OpenAI**: Automatic for any prompt with 1,024+ tokens. No code changes needed.
     Optional ``prompt_cache_key`` and ``prompt_cache_retention`` parameters allow
     routing hints and TTL control (``"in_memory"`` ≈ 5–10 min vs ``"24h"``).
   * **Anthropic**: Opt-in. Specific message blocks must be annotated with
     ``"cache_control": {"type": "ephemeral"}``. Anthropic charges for cache-write
     tokens (``cache_creation_input_tokens``) in addition to normal input tokens, so
     it is only cost-effective when the same annotated content is reused across multiple
     requests.
   * **Bedrock / Deepseek**: Follow the same pattern as OpenAI (automatic or opt-in
     depending on the model).

   LiteLLM can automatically inject ``cache_control`` annotations via
   ``cache_control_injection_points`` without requiring application code changes.

The combination of these two mechanisms must be evaluated against the call types
actually used in the platform. Currently several workflows rely on the OpenAI
Responses API, which makes LiteLLM proxy caching unavailable for those paths.

Decision
********

No single caching strategy is adopted globally. Instead, the following approach is
proposed as a baseline to be refined as usage patterns become clearer:

* **Proxy response caching** (Redis-backed) is enabled **only** for call types that
  are compatible with it (``acompletion``, ``atext_completion``, ``aembedding``).
  The ``supported_call_types`` setting in ``cache_params`` must explicitly exclude
  ``responses`` until LiteLLM adds support for that endpoint.

* **Prompt caching** is enabled where possible at the provider level:

  * For OpenAI-backed workflows, no code change is needed beyond ensuring system
    prompts exceed 1,024 tokens or structuring requests so the cacheable prefix is
    long enough.
  * For Anthropic-backed workflows, ``cache_control`` annotations are added to
    large, stable system-prompt blocks. Cost implications (write charges) must be
    assessed per workflow before enabling.
  * LiteLLM's ``cache_control_injection_points`` feature is preferred over manual
    annotation when the system message is the primary caching target.

* Cache TTL defaults to **600 seconds** for proxy caching. Workflows with
  highly dynamic outputs (e.g., chat with real-time context) should set ``no-store``
  on individual requests.

* Cache hits and ``cached_tokens`` values are monitored via LiteLLM's
  ``/cache/ping`` health endpoint and usage objects to validate cost savings.

Consequences
************

* Workflows using ``/chat/completions`` and ``/embeddings`` benefit from full
  response deduplication via Redis, reducing redundant API calls for repeated
  identical requests.
* Workflows using the OpenAI Responses API receive **no** proxy-level caching
  benefit until LiteLLM adds ``responses`` to its supported cache call types.
* Provider-side prompt caching provides latency and cost reductions for large,
  stable system prompts regardless of call type, including the Responses API.
* Enabling Anthropic prompt caching without usage analysis may **increase** costs
  due to cache-write token charges; this must be verified per workflow.
* Introducing Redis as a cache backend adds an infrastructure dependency that
  operators must provision and maintain.
