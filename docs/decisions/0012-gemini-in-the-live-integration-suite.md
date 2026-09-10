# 0012 - Gemini in the live integration suite

## Status

Accepted


## Context

ADR 0011 designed the live integration suite around OpenAI and Anthropic, and anticipated Gemini as a third provider. That anticipation carried one assumption: that Gemini, like OpenAI, would expose a server-side thread ID, so the threading tests (D, E, N, O, P) were listed as covering "OpenAI, Gemini". The ADR also twice referred readers to a *Gemini provider* section that was never written.

The suite ran on two providers for several months. Actually adding Gemini showed the assumption was wrong, and surfaced two things about the suite itself that 0011 could not have known.

## Decision

### Gemini is reached through Google AI Studio

`DEFAULT_GEMINI_MODEL` is `gemini/gemini-3.1-flash-lite`.

### Gemini declares one capability, and deliberately lacks two

**`requires_user_message`** — Gemini maps system messages to `system_instruction`, so a system-only request reaches the API with an empty `contents` array. LiteLLM does not fail on this; it injects a placeholder `" "` user turn, so the model is silently asked to respond to a single space. That is worse than an error, because the request still succeeds and the tests still pass.

Anthropic needed the same handling and already had it, as a hardcoded `provider == "anthropic"` branch in `adapt_to_provider`. That branch is now a capability shared by both providers.

**Not `server_side_thread_id`** — `ProviderConfigManager.get_provider_responses_api_config` returns `None` for Gemini, so `responses()` falls through to LiteLLM's completion bridge exactly as it does for Anthropic. There is no `previous_response_id` to chain. This is the assumption 0011 got wrong.

**Not `multi_turn_cache`** — Gemini does honour `cache_control`, but LiteLLM converts it into a server-side `CachedContent` resource and removes the cached messages from `contents`. Only the first contiguous run of marked messages is used, so the two deliberately non-contiguous breakpoints from ADR 0010 would be partially dropped — and in the initial-turn shape the whole request can end up inside the cache resource with nothing left to send. Caching Gemini needs its own breakpoint strategy and its own test.

### Retries live at the pytest layer, not in LiteLLM

Live providers intermittently answer 503 under load; the first Gemini runs lost several tests that way, each with a passing configuration twin in the same run. `litellm.num_retries` is not the way to absorb them:

- it routes through `completion_with_retries()`, which imports `tenacity` — not a LiteLLM dependency and not in `requirements/`, so the call raises `Exception("tenacity import failed ...")` in place of the provider error;
- the wrapper nulls `litellm.num_retries` before retrying and never restores it, making a module-level setting a one-shot for the whole process — and the one error it corrupts is whichever retryable error comes first, in practice a fault-tolerance test whose assertions accept any error and therefore hide it;
- the retry branch is gated on `call_type == "completion"`, and streaming failures surface during generator iteration, outside the wrapper's `try`/`except` entirely.

`make test-integration` therefore passes `--reruns 3 --reruns-delay 5`. `pytest-rerunfailures` was already a declared test dependency for this purpose. Reruns cost nothing on a green run, cover every call path including streaming, and are provider-agnostic; a deterministic failure still fails every attempt.

## Amendments to ADR 0011

0011 chose graceful degradation when a provider key is absent, but `judge.py` raised an authentication error when *its own* key was missing, failing every semantic-quality test for reasons unrelated to the provider under test. `Judge.ask()` now calls `pytest.skip` instead.

0011's test matrix should be read with these corrections:

| In 0011 | Actually |
|---|---|
| D, E, N, O listed as "OpenAI, Gemini" | OpenAI only — Gemini has no `server_side_thread_id` |
| P listed as "OpenAI, Gemini" | All providers — it threads `chat_history` itself, so it needs no capability |
| A, C, G, H, K, L, S, T, Z, AA listed as "OpenAI, Anthropic" | All providers, via `PROVIDERS` |
| M as two per-provider tests | One parametrised `test_streaming_with_response_format_clean_outcome` |
| References to a *Gemini provider* section | This ADR |

## Consequences

- Adding a provider is still a `PROVIDERS` entry plus a key in `integration_test_settings.py`, but a provider whose behaviour differs must have that difference declared in `_PROVIDER_CAPABILITIES` first. Capability-gated tests then skip on their own.
- `GEMINI_API_KEY` joins the CI secrets that need budget and rotation.
- LiteLLM strips `additionalProperties` from a `json_schema` before calling Gemini, because Gemini's schema type does not define that field and sending it is rejected. Gemini's own `responseSchema` still constrains output to the declared properties, so test S holds — but a Gemini failure there means the model went off-schema, not that it ignored a flag it never received.
- Gemini prompt caching remains unimplemented and untested. Enabling it is a separate decision.
