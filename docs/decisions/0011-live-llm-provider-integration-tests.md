# 0011 - Live LLM provider integration tests

## Status

Proposed

## Context

The existing test suite exercises every layer of the plugin — orchestrators, processors, API endpoints, session management — but every test mocks the LLM call itself. This means the tests verify that the plugin *plumbs* a request correctly to LiteLLM, but they cannot detect:

- A provider's API rejecting a request because of a changed model name, deprecated parameter, or schema enforcement rule.
- A structured-output contract (`response_format` / JSON schema) that the LLM silently ignores or returns in an unexpected shape.
- Thread-based context not surviving across turns on the provider's side.
- Responses that are syntactically correct but semantically unrelated to the question asked.
- Silent failures in error-recovery paths (e.g. stale thread IDs, unguarded `json.loads` calls) that only trigger under real API conditions.

These failure modes only surface against a real network call. A lightweight integration suite that runs on demand (not in every CI push) closes this gap without bloating the regular test runtime.

## Decision

Introduce a separate layer of live integration tests, isolated from the normal suite, that send actual requests to each configured LLM provider (OpenAI, Anthropic) and assert on real responses.

### Structure

```
backend/
├── integration_test_settings.py
└── tests/integration/
    ├── __init__.py
    ├── conftest.py
    ├── test_live_llm_providers.py     # A–F   happy-path baseline
    ├── test_fault_tolerance.py        # G, H   API rejections
    ├── test_streaming_edge_cases.py   # K, L, M, AI  streaming edge cases
    ├── test_threading.py              # N, O, P, Q, R  thread management
    ├── test_response_format.py        # S, T, V  schema depth
    ├── test_token_usage.py            # W, X, Y  usage tracking
    ├── test_educator_assistant.py     # Z, AA  structured-output quality
    ├── test_tool_calls.py             # AD, AE  tool-call round-trips
    └── test_semantic_quality.py       # AF, AG, AH  LLM-as-judge extensions
```

**`integration_test_settings.py`** — A Django settings module that inherits `test_settings` and overrides `AI_EXTENSIONS` with provider entries backed by environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Only activated when running the integration suite; `make test` continues to use `test_settings`.

**`tests/integration/conftest.py`** — Declares `PROVIDERS` (the parametrised list of provider slugs and their required env-var names), `skip_if_no_key` (runtime skip helper), `create_profile_and_scope` (creates `AIWorkflowProfile` + `AIWorkflowScope` with provider slug injected via `content_patch`), and shared fixtures (`course_key`, `location_id`, `live_user`, `live_api_client`).

The `integration_test_settings.py` targets `openai/gpt-4o-mini` and `anthropic/claude-haiku-3-5` — cheap, fast models appropriate for integration checks.

### Key design choices

**Automatic skip when keys are absent.** Parametrised tests call `skip_if_no_key` as their first statement; provider-specific tests use `@pytest.mark.skipif` evaluated at collection time. Both produce a clean skip rather than a failure in keyless environments.

**Provider override via `content_patch`.** Rather than creating new profile JSON templates on disk, each test injects the desired provider slug and any extra options into an existing base profile using the RFC 7386 merge-patch mechanism already supported by `AIWorkflowProfile`. This keeps test infrastructure thin and exercises the same config-merge path used in production.

**Bad credentials injected the same way.** Fault-tolerance tests override `options.api_key` or `options.model` via the same `content_patch` / `extra_llm_patch` mechanism, confirming that invalid configuration is surfaced as an error rather than silently producing a `completed` response.

**OpenEdX content is mocked; LLM call is real.** `OpenEdXProcessor` is patched to return a fixed string so tests do not depend on a running LMS. Only the LiteLLM network call is live, isolating the variable under test to the provider response.

**Thread and context tests bypass the API layer.** Tests that validate multi-turn behaviour instantiate `LLMProcessor` directly with a `MagicMock` session object. This avoids entanglement with `SubmissionProcessor`, which requires the submissions Django app. The mock session records attribute assignments (`remote_response_id`) so assertions can be made on them directly.

**`EducatorAssistantProcessor` called directly.** Educator tests instantiate `EducatorAssistantProcessor` with the schema loaded from `response_schemas/educator_quiz_questions.json` passed as `extra_params["response_format"]`, mirroring the production call path in `EducatorAssistantOrchestrator`. This avoids session and submission-processor complexity while exercising the real unguarded `json.loads` at line 83.

**`json.loads` interception.** Test AA patches `json.loads` inside the processor module to capture the raw LLM string before the processor consumes it. The captured string is independently validated, so the test fails with a clear message if the LLM ever returns non-JSON — a failure mode that would otherwise crash the processor with an unhandled `JSONDecodeError`.

**LLM-as-judge for semantic validation.** Tests F, AF, AG, and AH use a second LLM call as an evaluator: the primary response is fed back to the same provider with a strict system prompt that returns a JSON verdict (`yes` / `no`). This detects responses that are structurally valid but semantically incorrect.

**`live_llm` pytest marker.** All tests carry `@pytest.mark.live_llm`, declared in `tox.ini`. The normal suite excludes them with `-m "not live_llm"`; the integration suite selects only them with `-m live_llm`.

**Separate Makefile target.** `make test-integration` sets `DJANGO_SETTINGS_MODULE=integration_test_settings` inline and runs only `tests/integration/` with the `live_llm` marker. `make test` is unchanged.

### Test matrix

#### Baseline — happy path (`test_live_llm_providers.py`)

| # | Test name | Providers | What is validated |
|---|-----------|-----------|-------------------|
| A | `test_provider_returns_non_empty_response` | OpenAI, Anthropic | Status is `completed`; response string has more than 10 characters |
| B | `test_streaming_yields_content` | OpenAI, Anthropic | Response content type is `text/plain`; accumulated streaming bytes exceed 20 characters |
| C | `test_response_format_json_schema` | OpenAI, Anthropic | Response parses as valid JSON; required key `answer` is present and is a string |
| D | `test_threaded_stores_remote_response_id` | OpenAI only | `session.remote_response_id` is non-empty after the first `chat_with_context` call |
| E | `test_threaded_context_maintained_openai` | OpenAI only | A fact planted in turn one is recalled correctly in turn two of the same server-side thread |
| F | `test_llm_judge_response_relevance` | OpenAI, Anthropic | LLM-as-judge returns `yes` confirming the response is topically consistent with the source content |

#### Fault tolerance (`test_fault_tolerance.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| G | `test_invalid_api_key_does_not_return_completed` | OpenAI, Anthropic | HTTP 4xx/5xx or body without `status=completed`; no unhandled exception | `_handle_streaming_completion` broad-except masks auth failures; non-streaming path has no catch |
| H | `test_wrong_model_name_does_not_return_completed` | OpenAI, Anthropic | Error surfaced; no `completed` response with placeholder text | `adapt_to_provider` passes model name through without validation |

#### Streaming edge cases (`test_streaming_edge_cases.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| K | `test_streaming_handles_empty_delta_chunks` | OpenAI, Anthropic | No crash; no error marker in accumulated bytes | `content = chunk.choices[0].delta.content or ""` yields empty bytes silently |
| L | `test_streaming_long_response_arrives_completely` | OpenAI, Anthropic | All chunks arrive; final text >200 chars; no error marker | No check that stream fully drains before closing |
| M | `test_streaming_with_response_format_openai` / `test_streaming_with_response_format_anthropic_clean_outcome` | OpenAI / Anthropic | Valid streamable output OR clean rejection; no 500 crash | OpenAI does not support streaming + strict JSON schema in all model variants; Anthropic rejects it outright |
| AI | `test_healthy_stream_has_no_error_marker` | OpenAI, Anthropic | `"error_in_stream"` substring NOT in accumulated bytes | `\|\|{...}\|\|` error marker injected on streaming failure; must not appear in healthy call |

#### Thread / context management (`test_threading.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| N | `test_stale_thread_id_triggers_recovery` | OpenAI only | `previous_response_not_found` caught; stale ID replaced; valid response returned | Recovery hole in `threaded_orchestrator.py:153-159`; stale `remote_response_id` not auto-cleared |
| O | `test_conversation_clean_after_stale_thread_recovery` | OpenAI only | Second turn succeeds; response is grounded in current content | Recursive retry in `_call_responses_wrapper` has no max-retry guard |
| P | `test_three_turn_context_chain` | OpenAI only | Fact from turn 1 recalled correctly in turn 3 despite neutral turn 2 | Only 2-turn context was previously tested |
| Q | `test_anthropic_cache_hit_on_second_call` | Anthropic only | Second call's `usage.cache_read_input_tokens > 0` with large context | `multi_turn_cache` path in `providers/__init__.py`; no test that cache actually fires |
| R | `test_anthropic_cache_short_prompt_no_crash` | Anthropic only | No crash; valid response returned when prompt is below Anthropic's 1024-token cache minimum | Anthropic silently rejects cache for prompts <1024 tokens |

#### Response format depth (`test_response_format.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| S | `test_response_format_no_extra_keys` | OpenAI, Anthropic | Parsed response has EXACTLY the declared keys; no extras | Schema declared but enforcement depends on model compliance |
| T | `test_response_format_required_array_non_empty` | OpenAI, Anthropic | Returned array has ≥ 1 element | `educator_quiz_questions.json` has no `minItems`; LLM can return `[]` silently |
| V | `test_anthropic_streaming_with_strict_schema_no_crash` | Anthropic only | Clean error or graceful fallback; not a 500 crash | Anthropic does not support structured output + streaming in all API versions |

#### Token usage tracking (`test_token_usage.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| W | `test_usage_populated_after_non_streaming_call` | OpenAI, Anthropic | `usage` dict present; `total_tokens > 0`; `prompt_tokens` and `completion_tokens` both set | `self.usage = None` initial; only set if response carries usage; never validated downstream |
| X | `test_usage_populated_after_streaming_call` | OpenAI, Anthropic | After stream drains, `processor.get_usage()` returns non-None with `total_tokens > 0` | Final chunk carries usage only if `stream_options: {include_usage: true}` is sent |
| Y | `test_usage_with_tools_enabled_openai` | OpenAI only | `usage.total_tokens > 0` when tools schema is included in the prompt | Tool-call tokens may be omitted from usage in some providers |

#### EducatorAssistant & structured outputs (`test_educator_assistant.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| Z | `test_quiz_generation_returns_non_empty_problems` | OpenAI, Anthropic | `problems` list has ≥ 1 item; each item has all required fields (`display_name`, `question_html`, `problem_type`, `choices`); `collection_name` non-empty | No `minItems` constraint in `educator_quiz_questions.json`; LLM can return `[]` silently |
| AA | `test_quiz_generation_response_is_valid_json` | OpenAI, Anthropic | Raw LLM string captured before `json.loads`; independently verified as valid JSON | `json.loads` unguarded at `educator_assistant_processor.py:83` — any malformed LLM response crashes quiz generation in production |

#### Tool-call round-trips (`test_tool_calls.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| AD | `test_tool_call_pipeline_completes` | OpenAI only | Call completes without hang; non-empty response; usage populated | Tool executor logs errors and continues; no test that tool result actually reaches LLM |
| AE | `test_unknown_tool_name_returns_error_string` / `test_empty_available_tools_does_not_crash` | OpenAI only | Error string returned; processor completes; no unhandled exception | `tool_executor.py` uses `continue` on unknown tool; silently dropped |

#### Semantic quality (`test_semantic_quality.py`)

| # | Test name | Providers | Judge question | Risk caught |
|---|-----------|-----------|----------------|-------------|
| AF | `test_response_language_matches_content` | OpenAI, Anthropic | "Is the response in the same language as the content?" → yes | No language enforcement; model may respond in English for non-English content |
| AG | `test_response_does_not_hallucinate_beyond_content` | OpenAI, Anthropic | "Does the response contain only information from the provided content?" → yes | No grounding check; models confabulate on fictional/narrow content |
| AH | `test_response_not_truncated_mid_list` | OpenAI, Anthropic | "Does the response mention all five steps?" → yes | `MAX_TOKENS=500` cap may cut responses mid-sentence |

## Consequences

- Any developer with valid API keys can run `make test-integration` from the `backend/` directory and get immediate feedback on provider compatibility.
- CI pipelines that do not have API keys continue to run `make test` without disruption; live tests are automatically skipped.
- Adding a new LLM provider to the integration suite requires only a new entry in `PROVIDERS` (in `conftest.py`) and a matching key in `integration_test_settings.py`. No new test functions are needed for the parametrised cases; only thread-specific tests (D, E, N, O, P) may need provider-specific variants.
- Live tests consume real API credits on every run. Test models are chosen to minimise cost; the `MAX_TOKENS` cap is set conservatively at 500 tokens.
- The LLM-as-judge pattern (tests F, AF, AG, AH) is probabilistic: a judge model could theoretically return `no` for a correct response. The judge prompt and content are designed to minimise ambiguity, but occasional flakiness on semantically borderline responses should be expected and investigated case by case rather than treated as a systematic failure.
- Fault-tolerance tests (G, H) assert on error surfacing rather than on a specific HTTP status code, because the exception propagation path depends on the DRF view's error handler. This makes the assertions robust to future view refactors.
- The Anthropic cache test (Q) requires a large enough context to exceed the provider's 1024-token minimum for cache activation. If the prompt is too short, the test will report `cache_read_input_tokens = 0` without failing, indicating the cache threshold was not met rather than a bug in the integration.
