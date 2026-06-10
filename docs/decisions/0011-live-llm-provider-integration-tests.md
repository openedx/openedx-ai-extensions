# 0011 - Live LLM provider integration tests

## Status

Accepted

## Context

The existing test suite exercises every layer of the plugin — orchestrators, processors, API endpoints, session management — but every test mocks the LLM call itself. This means the tests verify that the plugin *plumbs* a request correctly to LiteLLM, but they cannot detect:

- A provider's API rejecting a request because of a changed model name, deprecated parameter, or schema enforcement rule.
- A structured-output contract (`response_format` / JSON schema) that the LLM silently ignores or returns in an unexpected shape.
- Thread-based context not surviving across turns on the provider's side.
- Responses that are syntactically correct but semantically unrelated to the question asked.
- Silent failures in error-recovery paths (e.g. stale thread IDs) that only trigger under real API conditions.

These failure modes only surface against a real network call. A lightweight integration suite that runs on every merge to main closes this gap: failures are caught before a release rather than discovered in production, without the cost of running on every push.

## Decision

Introduce a separate layer of live integration tests, isolated from the normal suite, that send actual requests to each configured LLM provider (OpenAI, Anthropic, Gemini) and assert on real responses.

### Structure

```
backend/
├── integration_test_settings.py
└── tests/integration/
    ├── __init__.py
    ├── conftest.py
    ├── test_live_llm_providers.py     # A, C, D, E  happy-path baseline
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

**`tests/integration/conftest.py`** — Declares `PROVIDERS` (the parametrised list of provider slugs and their required env-var names), `skip_if_no_key` (runtime skip helper), `create_profile_and_scope` (creates `AIWorkflowProfile` + `AIWorkflowScope` with provider slug injected via `content_patch`), `create_live_session` (creates a real `AIWorkflowSession` DB row for threading tests), `judge()` (shared LLM-as-judge helper used by semantic quality tests), and shared fixtures (`course_key`, `location_id`, `live_user`, `live_api_client`).

The `integration_test_settings.py` targets the current provider defaults for each configured provider. These model references should be reviewed and updated on a regular cadence (approximately monthly or bimonthly) to stay aligned with what is actually deployed in production.

### Key design choices

**Run trigger.** The integration suite runs on every merge to the main branch via CI, not on every push. This catches provider-side breakage before a release while keeping per-push CI fast. A failed integration run opens a new PR to fix; it does not block day-to-day development.

**Operational requirement: valid API keys with budget.** The CI environment must have `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` set with accounts that have sufficient token budget. Maintaining these credentials (rotation, budget monitoring) is an administrative responsibility alongside the technical test suite. Parametrised tests skip automatically at runtime when a key is absent, so the suite degrades gracefully rather than failing when a key is missing.

**Provider override via `content_patch`.** Rather than creating new profile JSON templates on disk, each test injects the desired provider slug and any extra options into an existing base profile using the RFC 7386 merge-patch mechanism already supported by `AIWorkflowProfile`. This keeps test infrastructure thin and exercises the same config-merge path used in production.

**Bad credentials injected the same way.** Fault-tolerance tests override `options.api_key` or `options.model` via the same `content_patch` / `extra_llm_patch` mechanism, confirming that invalid configuration is surfaced as an error rather than silently producing a `completed` response.

**OpenEdX content is mocked; LLM call is real.** `OpenEdXProcessor` is patched to return a fixed string so tests do not depend on a running LMS or a Tutor deployment. Only the LiteLLM network call is live, isolating the variable under test to the provider response.

**Thread and context tests use real DB sessions.** Tests N, O, and P use `create_live_session`, which creates real `AIWorkflowSession` rows so that `session.save()` exercises the actual persistence layer. Test D (`test_threaded_stores_remote_response_id`) still uses `MagicMock` because it only checks that the attribute is set, not that it survives a round-trip to the database. `SubmissionProcessor` is not required by these tests.

**LLM-as-judge for semantic validation.** Tests AF, AG, and AH use a second LLM call as an evaluator: the primary response is fed back with a strict system prompt that returns a JSON verdict (`yes` / `no`).

**`live_llm` pytest marker.** All tests carry `@pytest.mark.live_llm`, declared in `tox.ini`. The normal suite excludes them with `-m "not live_llm"`; the integration suite selects only them with `-m live_llm`.

**Separate Makefile target.** `make test-integration` sets `DJANGO_SETTINGS_MODULE=integration_test_settings` inline and runs only `tests/integration/` with the `live_llm` marker. `make test` is unchanged. The exact invocation will evolve once the suite is wired into GitHub Actions CI.

### Test matrix

#### Baseline — happy path (`test_live_llm_providers.py`)

| # | Test name | Providers | What is validated |
|---|-----------|-----------|-------------------|
| A | `test_provider_returns_non_empty_response` | OpenAI, Anthropic | Status is `completed`; response string has more than 10 characters |
| C | `test_response_format_json_schema` | OpenAI, Anthropic | Response parses as valid JSON; required key `answer` is present and is a string |
| D | `test_threaded_stores_remote_response_id` | OpenAI, Gemini | `session.remote_response_id` is non-empty after the first `chat_with_context` call (uses `MagicMock` session) |
| E | `test_threaded_context_maintained_openai` | OpenAI, Gemini | Turn 0 initialises the remote thread (system messages only). Turn 1 plants a fact via `previous_response_id`; turn 2 recalls it. Uses a real DB session via `create_live_session`. |

Tests B (`test_streaming_yields_content`) and F (`test_llm_judge_response_relevance`) were removed: B is superseded by the deeper test L in `test_streaming_edge_cases.py`; F is superseded by the more specific hallucination and grounding checks in `test_semantic_quality.py`.

Tests D and E are scoped to providers exposing a server-side thread/response ID (the `server_side_thread_id` capability in `_PROVIDER_CAPABILITIES`): OpenAI and Gemini. See *Gemini provider* below for Gemini-specific notes.

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
| M | `test_streaming_with_response_format_*` | OpenAI / Anthropic | Valid streamable output OR clean rejection; no 500 crash | Streaming + strict JSON schema is unsupported in some provider/model combinations; this incompatibility should also be enforced at the code level by mapping it in `_PROVIDER_CAPABILITIES` so the plugin rejects the combination before calling the provider |
| AI | `test_healthy_stream_has_no_error_marker` | OpenAI, Anthropic | `"error_in_stream"` substring NOT in accumulated bytes | `\|\|{...}\|\|` error marker injected on streaming failure; must not appear in healthy call |

#### Thread / context management (`test_threading.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| N | `test_stale_thread_id_triggers_recovery` | OpenAI, Gemini | `previous_response_not_found` caught; stale ID replaced; valid response returned | `_call_responses_wrapper` checked `e.code` for the error string, but litellm sets `e.code = None` (passes `body=None` to parent constructor), so the check never matched and the exception was re-raised. Fixed to check `str(e)` which includes the full provider JSON. |
| O | `test_conversation_clean_after_stale_thread_recovery` | OpenAI, Gemini | Second turn succeeds; response is grounded in current content | Recursive retry in `_call_responses_wrapper` has no max-retry guard |
| P | `test_three_turn_context_chain` | OpenAI, Gemini | Fact planted in turn 1 recalled correctly in turn 3 despite neutral turn 2. Turn 0 initialises the remote thread (system messages only); turns 1–3 chain via `previous_response_id`. | User input on the first call is not sent to OpenAI under the current design (only system messages are sent on thread initialisation); a turn 0 is required before planting the memorable fact. |
| Q | `test_anthropic_cache_hit_on_second_call` | Anthropic only | Second call's `usage.cache_read_input_tokens > 0` with large context | `multi_turn_cache` path in `providers/__init__.py`; no test that cache actually fires. Feasibility to be confirmed during implementation — may be left out if impractical. |
| R | `test_anthropic_cache_short_prompt_no_crash` | Anthropic only | No crash; valid response returned when prompt is below Anthropic's 1024-token cache minimum | Anthropic silently rejects cache for prompts <1024 tokens |

Tests N, O, and P are likewise scoped to `server_side_thread_id` providers (OpenAI and Gemini; see *Gemini provider*).

#### Response format depth (`test_response_format.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| S | `test_response_format_no_extra_keys` | OpenAI, Anthropic | Parsed response has EXACTLY the declared keys; no extras | Schema declared but enforcement depends on model compliance |
| T | `test_response_format_required_array_non_empty` | OpenAI, Anthropic | Returned array has ≥ 1 element | `educator_quiz_questions.json` has no `minItems`; LLM can return `[]` silently |
| V | `test_anthropic_streaming_with_strict_schema_no_crash` | Anthropic only | Clean error or graceful fallback; not a 500 crash | Anthropic does not support structured output + streaming in all API versions; longer term this combination should be blocked in `_PROVIDER_CAPABILITIES` |

#### Token usage tracking (`test_token_usage.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| W | `test_usage_populated_after_non_streaming_call` | OpenAI, Anthropic | `usage` dict present; `total_tokens > 0`; `prompt_tokens` and `completion_tokens` both set | `self.usage = None` initial; only set if response carries usage. Note: the plugin makes no public promises about token count values — consider whether this coverage is better placed in unit tests. |
| X | `test_usage_populated_after_streaming_call` | OpenAI, Anthropic | After stream drains, `processor.get_usage()` returns non-None with `total_tokens > 0` | Final chunk carries usage only if `stream_options: {include_usage: true}` is sent. See W note above. |
| Y | `test_usage_with_tools_enabled_openai` | OpenAI only | `usage.total_tokens > 0` when tools schema is included in the prompt | Tool-call tokens may be omitted from usage in some providers. See W note above. |

#### EducatorAssistant & structured outputs (`test_educator_assistant.py`)

| # | Test name | Providers | What is validated | Risk caught |
|---|-----------|-----------|-------------------|-------------|
| Z | `test_quiz_generation_returns_non_empty_problems` | OpenAI, Anthropic | `problems` list has ≥ 1 item; each item has all required fields (`display_name`, `question_html`, `problem_type`, `choices`); `collection_name` non-empty | No `minItems` constraint in `educator_quiz_questions.json`; LLM can return `[]` silently |
| AA | `test_quiz_generation_response_is_valid_json` | OpenAI, Anthropic | Processor completes with `status=success`; response is a parsed dict with `collection_name` present; any `JSONDecodeError` from the unguarded call surfaces naturally as a test failure | `json.loads` unguarded at `educator_assistant_processor.py:83`; schema we control constrains LLM to valid JSON via structured outputs |

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

Test AH feeds the LLM a fixed content fixture describing a five-step process (e.g. a numbered how-to with steps 1-5); the judge checks that the response covers all five, so a mid-list truncation is caught even if the prose up to that point looks complete.

Tests AF, AG, and AH are marked `@pytest.mark.xfail(strict=False)`: weaker-reasoning providers/models can fail the judge's yes/no check on otherwise-correct responses, and these tests must not stop the rest of the integration suite.

### Gemini provider

Gemini is included in `PROVIDERS` and `_PROVIDER_CAPABILITIES` as a `server_side_thread_id` provider, alongside OpenAI: it supports server-side conversation threading via `previous_interaction_id`, with interactions stored for 55 days on the paid tier and 1 day on the free tier. Tests D, E, N, O, and P run against Gemini accordingly, and the stale-thread recovery test (N) must account for its 55-day expiry window.

## Consequences

- Any developer with valid API keys can run `make test-integration` from the `backend/` directory and get immediate feedback on provider compatibility. The exact CI invocation will be defined when the suite is wired into GitHub Actions.
- The CI environment must have `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` set with sufficient token budget; maintaining these credentials is an ongoing administrative responsibility.
- Adding a new LLM provider to the integration suite requires only a new entry in `PROVIDERS` (in `conftest.py`) and a matching key in `integration_test_settings.py`. No new test functions are needed for the parametrised cases; only thread-specific tests (D, E, N, O, P) may need provider-specific variants.
- Live tests consume real API credits on every run. Test models should match the production provider defaults; LLM-as-judge tests should use a reasoning-focused model. Both categories should be reviewed on a regular cadence.
- The LLM-as-judge pattern (tests AF, AG, AH) is optimised for quality, not speed — using a reasoning model for judgement is intentional. These tests depend on the target model adhering to a strict yes/no judge prompt and may fail for some provider/model combinations regardless of response quality. They are marked `xfail(strict=False)` so a provider with weaker reasoning cannot fail the whole integration run, until a more robust grounding/evaluation approach is implemented.
- Fault-tolerance tests (G, H) assert on error surfacing rather than on a specific HTTP status code, because the exception propagation path depends on the DRF view's error handler. This makes the assertions robust to future view refactors.
- The Anthropic cache test (Q) requires a large enough context to exceed the provider's 1024-token minimum for cache activation. Feasibility will be confirmed during implementation; if impractical, it will be left out.
- The token-usage tests (W, X, Y) cover behaviour the plugin makes no public promises about. If they prove difficult to maintain or add noise to the integration run, they should be moved to unit tests instead.
