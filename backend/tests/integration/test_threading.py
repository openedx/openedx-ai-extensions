"""
Validates that stale / expired remote thread IDs are recovered from
without crashing, that the recovered conversation starts cleanly, that
multi-turn context persists across three turns, and that Anthropic
prompt caching fires (or at least does not crash) at various token sizes.

Every test in this file uses a real AIWorkflowSession DB row (via
create_live_session) rather than a mock, so session.save() exercises the
actual persistence layer.
"""

import pytest

from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor

from .conftest import PROVIDERS, create_live_session, skip_if_no_key, skip_unless_capability
from .sample_content import DUMMY_CONTENT, LONG_SYSTEM_CONTEXT, SHORT_CONTENT

ALREADY_EXPIRED_THREAD_ID = (
    "resp_bGl0ZWxsbTpjdXN0b21fbGxtX3Byb3ZpZGVyOm9wZW5haTttb2RlbF9pZDpOb25lO3Jlc3BvbnNlX2lkOnJlc3BfMDI5MTVhYjk4Mjc4"
    "ODVhMTAwNmEwZTNhMWQ1NjY0ODE5NWJmOTUyYWIxYTExYjE3ZmQ="
)

_OPENAI_CONFIG = {
    "LLMProcessor": {
        "provider": "test_openai",
        "stream": False,
        "function": "chat_with_context",
    }
}


@pytest.mark.live_llm
@pytest.mark.django_db
@skip_unless_capability("server_side_thread_id")
def test_stale_thread_id_triggers_recovery(live_user, course_key):
    """
    When session.remote_response_id points to a non-existent / expired
    OpenAI thread, the processor must catch previous_response_not_found,
    clear the stale ID, start a fresh thread, and return a valid response.
    """
    session = create_live_session(
        live_user, course_key,
        remote_response_id=ALREADY_EXPIRED_THREAD_ID,
    )

    processor = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    result = processor.process(
        context=DUMMY_CONTENT,
        input_data="Hello, please introduce yourself briefly.",
    )

    assert result.get("status") == "success", f"Expected success after recovery, got: {result}"
    assert result.get("response"), "Expected non-empty response after thread recovery"

    session.refresh_from_db()
    assert session.remote_response_id != ALREADY_EXPIRED_THREAD_ID, (
        "remote_response_id was not updated after stale-thread recovery"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@skip_unless_capability("server_side_thread_id")
def test_conversation_clean_after_stale_thread_recovery(live_user, course_key):
    """
    After stale-thread recovery, a second call on the same session must
    succeed and recall a fact planted in turn 1 — proving the recovered
    thread actually carries turn-1 context forward, not just that turn 2
    independently produces a plausible answer. The planted number is not in
    DUMMY_CONTENT or inferable from general knowledge, so the model can only
    recall it if turn 2 has real access to turn 1. Framed as a "lucky number"
    rather than an ID/identifier to avoid PII-refusal false negatives.
    """
    session = create_live_session(
        live_user, course_key,
        remote_response_id=ALREADY_EXPIRED_THREAD_ID,
    )

    # Turn 1 — recovery happens here
    proc1 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    result1 = proc1.process(
        context=DUMMY_CONTENT,
        input_data="My lucky number is 9142. Just say 'Got it'.",
    )
    assert result1.get("response"), "Turn 1 must produce a response for this test to be meaningful"

    # Turn 2 — same session, recovered thread
    session.refresh_from_db()
    proc2 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    result2 = proc2.process(
        context=DUMMY_CONTENT,
        input_data="What is my lucky number?",
    )

    assert result2.get("status") == "success", f"Turn 2 failed: {result2}"
    response_text = result2.get("response") or ""
    assert "9142" in response_text, (
        f"Expected '9142' in turn-2 response (recalled from turn 1), got: {response_text}"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_three_turn_context_chain(provider_slug, env_var, live_user, course_key):
    """
    A fact planted in turn 1 must still be recalled in turn 3, even after
    a neutral turn 2 that does not reference it. Multi-turn context retention
    is a general guarantee of the processor — providers with server-side
    threading (e.g. OpenAI) chain via previous_response_id, while others
    (e.g. Anthropic) need the prior turns resent as chat_history — so this
    runs against every configured provider rather than just OpenAI.

    LLMProcessor itself never auto-reconstructs chat_history (that's the
    caller's job — see ThreadedLLMResponse.run); since this test calls
    LLMProcessor directly, it threads chat_history between calls itself so
    non-OpenAI providers actually receive turn 1/2 on later calls instead of
    relying solely on previous_response_id (OpenAI-only).
    """
    skip_if_no_key(env_var)
    config = {
        "LLMProcessor": {
            "provider": provider_slug,
            "stream": False,
            "function": "chat_with_context",
        }
    }

    session = create_live_session(live_user, course_key)
    chat_history = []

    # Turn 0 — initialise the thread
    r0 = LLMProcessor(config=config, user_session=session).process(
        context=DUMMY_CONTENT, input_data="Start.", chat_history=chat_history
    )
    chat_history.append({"role": "user", "content": "Start."})
    chat_history.append({"role": "assistant", "content": r0.get("response") or ""})
    session.refresh_from_db()

    # Turn 1 — plant memorable fact
    proc1 = LLMProcessor(config=config, user_session=session)
    r1 = proc1.process(
        context=DUMMY_CONTENT,
        input_data="My favourite colour is TURQUOISE. Just say 'Got it'.",
        chat_history=chat_history,
    )
    assert r1.get("response"), "Turn 1 must return a response"
    chat_history.append({"role": "assistant", "content": r1.get("response") or ""})

    # Turn 2 — neutral noise turn
    session.refresh_from_db()
    proc2 = LLMProcessor(config=config, user_session=session)
    r2 = proc2.process(
        context=DUMMY_CONTENT,
        input_data="Tell me one thing about Python in one sentence.",
        chat_history=chat_history,
    )
    assert r2.get("response"), "Turn 2 must return a response"
    chat_history.append({"role": "assistant", "content": r2.get("response") or ""})

    # Turn 3 — recall the fact from turn 1
    session.refresh_from_db()
    proc3 = LLMProcessor(config=config, user_session=session)
    r3 = proc3.process(
        context=DUMMY_CONTENT,
        input_data="What is my favourite colour?",
        chat_history=chat_history,
    )

    assert r3.get("status") == "success", f"Turn 3 failed: {r3}"
    response_text = (r3.get("response") or "").lower()
    assert "turquoise" in response_text, (
        f"Expected 'turquoise' in turn-3 response, got: {r3.get('response')}"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@skip_unless_capability("multi_turn_cache")
def test_anthropic_cache_hit_on_second_call(live_user, course_key):
    """
    When the same large system context is sent twice to Anthropic, the
    second call's usage should report cache_read_input_tokens > 0,
    confirming the cache_control prefix written by the first call was
    reused. claude-haiku-4-5's cache minimum is 4096 tokens;
    LONG_SYSTEM_CONTEXT comfortably exceeds it.

    Uses a real AIWorkflowSession (like the other threading tests) rather
    than a MagicMock, so any session.save() call this code path makes is
    actually exercised instead of silently swallowed.
    """
    config = {
        "LLMProcessor": {
            "provider": "test_anthropic",
            "stream": False,
            "function": "summarize_content",
        }
    }

    session = create_live_session(live_user, course_key)

    # First call — warms the cache
    proc1 = LLMProcessor(config=config, user_session=session)
    r1 = proc1.process(context=LONG_SYSTEM_CONTEXT, input_data="Summarize this in one sentence.")
    assert r1.get("status") == "success", f"First call failed: {r1}"

    # Second call — should hit the cache
    session.refresh_from_db()
    proc2 = LLMProcessor(config=config, user_session=session)
    r2 = proc2.process(context=LONG_SYSTEM_CONTEXT, input_data="Summarize this in one sentence.")
    assert r2.get("status") == "success", f"Second call failed: {r2}"

    usage = proc2.get_usage()
    assert usage is not None, "Expected usage to be populated on second call"
    cache_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
    assert cache_tokens > 0, (
        f"Expected cache_read_input_tokens > 0 on second call. usage={usage}"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_cache_short_prompt_no_crash(provider_slug, env_var, live_user, course_key):
    """
    Setting cache=True must never crash, regardless of whether the provider
    actually supports a caching feature. Providers without "multi_turn_cache"
    in _PROVIDER_CAPABILITIES (e.g. OpenAI) should just ignore the flag;
    Anthropic silently ignores cache_control for prompts below the model's
    minimum (4096 tokens for claude-haiku-4-5) too. Either way, a valid
    response is returned with no error, even if no cache tokens are reported.

    Uses a real AIWorkflowSession so this exercises the same persistence
    path as every other test in this file, regardless of provider.
    """
    skip_if_no_key(env_var)
    config = {
        "LLMProcessor": {
            "provider": provider_slug,
            "stream": False,
            "function": "summarize_content",
            "cache": True,
        }
    }

    session = create_live_session(live_user, course_key)
    processor = LLMProcessor(config=config, user_session=session)
    result = processor.process(context=SHORT_CONTENT, input_data="Summarize this.")

    assert result.get("status") == "success", (
        f"Short-prompt cache call failed: {result}"
    )
    assert result.get("response"), "Expected non-empty response"
