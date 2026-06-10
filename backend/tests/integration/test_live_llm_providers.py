"""
Live LLM provider integration tests.

Tests here call real LLM APIs and are skipped automatically when the required
API key env vars are absent, making the suite CI-safe.
"""

import json
import os
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from .conftest import PROVIDERS, create_live_session, create_profile_and_scope, skip_if_no_key


DUMMY_CONTENT = (
    "Python is a high-level interpreted programming language created by Guido van Rossum. "
    "It emphasises code readability using significant indentation. "
    "Python supports multiple programming paradigms and has a large standard library."
)

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)

CONTEXT_JSON_TEMPLATE = json.dumps({
    "courseId": "course-v1:edX+LiveTest+Demo_Course",
    "locationId": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "uiSlotSelectorId": "live-test-slot",
})


def _workflows_url_with_context():
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    return f"{url}?{urlencode({'context': CONTEXT_JSON_TEMPLATE})}"


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_provider_returns_non_empty_response(
    provider_slug, env_var, live_api_client, course_key
):
    """Provider returns a non-empty completed response for a content summary request."""
    skip_if_no_key(env_var)
    create_profile_and_scope(provider_slug, course_key, "base/summary.json", slug_suffix="basic")

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = live_api_client.post(
            _workflows_url_with_context(),
            data=json.dumps({"action": "run", "user_input": {}}),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed"
    assert len(data.get("response", "")) > 10



_ANSWER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_response_format_json_schema(
    provider_slug, env_var, live_api_client, course_key
):
    """Provider respects json_schema response_format and returns parseable JSON with required keys."""
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="json-schema",
        extra_llm_patch={"options": {"response_format": _ANSWER_SCHEMA}},
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = live_api_client.post(
            _workflows_url_with_context(),
            data=json.dumps({"action": "run", "user_input": {}}),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed"
    parsed = json.loads(data["response"])
    assert "answer" in parsed, f"'answer' key missing from: {parsed}"
    assert isinstance(parsed["answer"], str)


@pytest.mark.live_llm
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_threaded_stores_remote_response_id():
    """After first threaded call, OpenAI response ID is persisted on the session object."""
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    config = {
        "LLMProcessor": {
            "provider": "test_openai",
            "stream": False,
            "function": "chat_with_context",
        }
    }
    session = MagicMock()
    session.remote_response_id = None

    processor = LLMProcessor(config=config, user_session=session)
    result = processor.process(
        context=DUMMY_CONTENT,
        input_data="Hello! Briefly say you can help.",
    )

    assert result.get("status") == "success"
    assert result.get("response"), "Expected non-empty response"
    assert session.remote_response_id is not None, (
        "remote_response_id should be set after first OpenAI threaded call"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_threaded_context_maintained_openai(live_user, course_key):
    """
    Server-side thread recalls a user-stated fact across turns.

    Turn 0 initialises the remote thread (system messages only — no user input
    reaches OpenAI on the first call with the current logic).  Turns 1 and 2
    are the meaningful user turns: MANGO is planted in turn 1 (sent via
    previous_response_id) and recalled in turn 2.
    """
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    config = {
        "LLMProcessor": {
            "provider": "test_openai",
            "stream": False,
            "function": "chat_with_context",
        }
    }

    session = create_live_session(live_user, course_key)

    # Turn 0 — initialise the remote thread (system messages only)
    proc0 = LLMProcessor(config=config, user_session=session)
    proc0.process(context=DUMMY_CONTENT, input_data="Start.")
    session.refresh_from_db()

    # Turn 1 — plant a memorable fact (sent as user message via previous_response_id)
    proc1 = LLMProcessor(config=config, user_session=session)
    result1 = proc1.process(
        context=DUMMY_CONTENT,
        input_data="My secret word is MANGO. Just say 'Got it'.",
    )
    assert result1.get("response"), "Turn 1 must return a response"
    session.refresh_from_db()

    # Turn 2 — ask about the fact; remote_response_id chains the thread
    proc2 = LLMProcessor(config=config, user_session=session)
    result2 = proc2.process(
        context=DUMMY_CONTENT,
        input_data="What is my secret word?",
    )

    response_text = (result2.get("response") or "").lower()
    assert "mango" in response_text, (
        f"Expected 'mango' in second-turn response, got: {result2.get('response')}"
    )


