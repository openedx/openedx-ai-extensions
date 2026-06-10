"""
Validates that stale / expired remote thread IDs are recovered from
without crashing, that the recovered conversation starts cleanly, that
multi-turn context persists across three turns, and that Anthropic
prompt caching fires (or at least does not crash) at various token sizes.

Threading tests (N, O, P) use real AIWorkflowSession DB rows so that
session.save() exercises the actual persistence layer rather than a mock.
"""

import os
from unittest.mock import MagicMock

import pytest

from .conftest import create_live_session

DUMMY_CONTENT = (
    "Python is a high-level interpreted programming language. "
    "It uses indentation for code blocks and supports multiple paradigms."
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
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_stale_thread_id_triggers_recovery(live_user, course_key):
    """
    When session.remote_response_id points to a non-existent / expired
    OpenAI thread, the processor must catch previous_response_not_found,
    clear the stale ID, start a fresh thread, and return a valid response.
    """
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    session = create_live_session(
        live_user, course_key,
        remote_response_id="resp_fake_expired_thread_id_xyz_000000",
    )

    processor = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    result = processor.process(
        context=DUMMY_CONTENT,
        input_data="Hello, please introduce yourself briefly.",
    )

    assert result.get("status") == "success", f"Expected success after recovery, got: {result}"
    assert result.get("response"), "Expected non-empty response after thread recovery"

    session.refresh_from_db()
    assert session.remote_response_id != "resp_fake_expired_thread_id_xyz_000000", (
        "remote_response_id was not updated after stale-thread recovery"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_conversation_clean_after_stale_thread_recovery(live_user, course_key):
    """
    After stale-thread recovery, a second call on the same session must
    succeed and produce a coherent response grounded in the provided content.
    """
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    session = create_live_session(
        live_user, course_key,
        remote_response_id="resp_fake_expired_thread_id_xyz_000000",
    )

    # Turn 1 — recovery happens here
    proc1 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    result1 = proc1.process(
        context=DUMMY_CONTENT,
        input_data="Hello, please introduce yourself briefly.",
    )
    assert result1.get("response"), "Turn 1 must produce a response for test O to be meaningful"

    # Turn 2 — same session, recovered thread
    session.refresh_from_db()
    proc2 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    result2 = proc2.process(
        context=DUMMY_CONTENT,
        input_data="What programming language are we discussing?",
    )

    assert result2.get("status") == "success", f"Turn 2 failed: {result2}"
    response_text = (result2.get("response") or "").lower()
    assert len(response_text) > 5, "Turn 2 produced an empty response"
    assert "python" in response_text, (
        f"Expected 'python' in turn-2 response (grounded in content), got: {result2.get('response')}"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_three_turn_context_chain(live_user, course_key):
    """
    A fact planted in turn 1 must still be recalled in turn 3, even after
    a neutral turn 2 that does not reference it.  Verifies that the server-
    side thread correctly chains three consecutive turns.
    """
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    session = create_live_session(live_user, course_key)

    # Turn 0 — initialise the remote thread (system messages only; no user input
    # reaches OpenAI on the first call with the current logic)
    LLMProcessor(config=_OPENAI_CONFIG, user_session=session).process(
        context=DUMMY_CONTENT, input_data="Start."
    )
    session.refresh_from_db()

    # Turn 1 — plant memorable fact (sent via previous_response_id)
    proc1 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    r1 = proc1.process(context=DUMMY_CONTENT, input_data="My favourite colour is TURQUOISE. Just say 'Got it'.")
    assert r1.get("response"), "Turn 1 must return a response"

    # Turn 2 — neutral noise turn
    session.refresh_from_db()
    proc2 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    r2 = proc2.process(context=DUMMY_CONTENT, input_data="Tell me one thing about Python in one sentence.")
    assert r2.get("response"), "Turn 2 must return a response"

    # Turn 3 — recall the fact from turn 1
    session.refresh_from_db()
    proc3 = LLMProcessor(config=_OPENAI_CONFIG, user_session=session)
    r3 = proc3.process(context=DUMMY_CONTENT, input_data="What is my favourite colour?")

    assert r3.get("status") == "success", f"Turn 3 failed: {r3}"
    response_text = (r3.get("response") or "").lower()
    assert "turquoise" in response_text, (
        f"Expected 'turquoise' in turn-3 response, got: {r3.get('response')}"
    )


_LONG_SYSTEM_CONTEXT = (
    "The history of computing spans several decades. "
    "From vacuum tubes to transistors to integrated circuits, each era "
    "brought dramatic improvements in speed, size, and cost. "
    "ENIAC (1945) was the first general-purpose electronic computer, "
    "weighing 30 tons and occupying an entire room. "
    "The invention of the transistor in 1947 at Bell Labs was a watershed moment, "
    "enabling miniaturisation that made personal computers possible. "
    "Intel released the first commercial microprocessor, the 4004, in 1971. "
    "The IBM PC in 1981 standardised the personal computer market. "
    "Tim Berners-Lee invented the World Wide Web in 1989, transforming computing. "
    "The rise of smartphones in the 2000s put computing in every pocket. "
    "Cloud computing emerged in the 2010s, shifting workloads to remote data centres. "
    "Today artificial intelligence, driven by GPUs and large language models, "
    "represents the next major inflection point in the history of computing technology. "
) * 4  # Repeat to exceed Anthropic's 1024-token minimum for cache activation


@pytest.mark.live_llm
@pytest.mark.xfail(
    strict=False,
    reason=(
        "config 'cache: True' enables litellm semantic caching (Redis), not Anthropic prompt "
        "caching. Anthropic prompt caching requires cache_control headers on messages, which "
        "the processor does not yet add. cache_read_input_tokens will remain 0 until implemented."
    ),
)
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_anthropic_cache_hit_on_second_call():
    """
    When the same large system context is sent twice to Anthropic with
    caching enabled, the second call's usage should report
    cache_read_input_tokens > 0, confirming the cache prefix fired.
    Anthropic requires > 1024 tokens in the cacheable prefix.
    """
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    config = {
        "LLMProcessor": {
            "provider": "test_anthropic",
            "stream": False,
            "function": "summarize_content",
            "cache": True,
        }
    }

    # First call — warms the cache
    proc1 = LLMProcessor(config=config, user_session=MagicMock(remote_response_id=None))
    r1 = proc1.process(context=_LONG_SYSTEM_CONTEXT, input_data="Summarize this in one sentence.")
    assert r1.get("status") == "success", f"First call failed: {r1}"

    # Second call — should hit the cache
    proc2 = LLMProcessor(config=config, user_session=MagicMock(remote_response_id=None))
    r2 = proc2.process(context=_LONG_SYSTEM_CONTEXT, input_data="Summarize this in one sentence.")
    assert r2.get("status") == "success", f"Second call failed: {r2}"

    usage = proc2.get_usage()
    if usage is not None:
        cache_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
        assert cache_tokens > 0, (
            f"Expected cache_read_input_tokens > 0 on second call. usage={usage}"
        )


_SHORT_CONTENT = "Python uses indentation to define code blocks."


@pytest.mark.live_llm
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_anthropic_cache_short_prompt_no_crash():
    """
    Anthropic silently ignores cache_control for prompts below ~1024 tokens.
    Enabling cache on a short prompt must not crash — a valid response is
    returned with no error, even if no cache tokens are reported.
    """
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    config = {
        "LLMProcessor": {
            "provider": "test_anthropic",
            "stream": False,
            "function": "summarize_content",
            "cache": True,
        }
    }

    processor = LLMProcessor(config=config, user_session=MagicMock(remote_response_id=None))
    result = processor.process(context=_SHORT_CONTENT, input_data="Summarize this.")

    assert result.get("status") == "success", (
        f"Short-prompt cache call failed: {result}"
    )
    assert result.get("response"), "Expected non-empty response"
