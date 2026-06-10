"""
Streaming edge cases.

All tests send real LLM requests and verify that streaming handles
unusual or boundary conditions without crashing.
"""

import json
import os
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from .conftest import PROVIDERS, create_profile_and_scope, skip_if_no_key

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)

DUMMY_CONTENT = (
    "Python is a high-level interpreted programming language created by Guido van Rossum. "
    "It emphasises code readability using significant indentation. "
    "Python supports multiple programming paradigms and has a large standard library."
)

CONTEXT_JSON = json.dumps({
    "courseId": "course-v1:edX+LiveTest+Demo_Course",
    "locationId": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "uiSlotSelectorId": "live-test-slot",
})

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


def _post_workflow(client):
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    qs = urlencode({"context": CONTEXT_JSON})
    return client.post(
        f"{url}?{qs}",
        data=json.dumps({"action": "run", "user_input": {}}),
        content_type="application/json",
    )


def _drain_stream(response):
    return b"".join(response.streaming_content).decode("utf-8")


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_streaming_handles_empty_delta_chunks(
    provider_slug, env_var, live_api_client, course_key
):
    """
    Streaming must not crash when the provider sends chunks with empty or
    None delta.content (common at stream start/end and during tool calls).
    """
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="stream-k",
        extra_llm_patch={"stream": True},
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code == 200
    content = _drain_stream(response)
    assert "error_in_stream" not in content, (
        f"Streaming failed with error marker: {content[:300]}"
    )
    assert len(content) > 0, "Streaming returned zero bytes"


_LONG_CONTENT = (
    "The history of computing spans several decades and encompasses many "
    "technological breakthroughs. From vacuum tubes to transistors to "
    "integrated circuits, each era brought dramatic improvements in speed, "
    "size, and cost. Key milestones include ENIAC (1945), the invention of "
    "the transistor (1947), the first microprocessor (1971), and the rise "
    "of personal computers in the 1980s. The Internet transformed computing "
    "in the 1990s, followed by mobile computing and cloud services in the 2000s. "
    "Today, artificial intelligence and quantum computing represent the next "
    "frontier of technological advancement in the computing field."
)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_streaming_long_response_arrives_completely(
    provider_slug, env_var, live_api_client, course_key
):
    """
    A prompt designed to produce a longer response must arrive fully —
    accumulated text should exceed 200 characters with no error marker.
    """
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="stream-l",
        extra_llm_patch={"stream": True},
    )

    with patch(OPENEDX_PATCH, return_value=_LONG_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code == 200
    content = _drain_stream(response)
    assert "error_in_stream" not in content, f"Stream error: {content[:300]}"
    assert len(content) > 200, (
        f"Expected >200 chars for long response, got {len(content)}: {content[:200]}"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_streaming_with_response_format_openai(live_api_client, course_key):
    """
    OpenAI streaming with a json_schema response_format must either yield
    valid content or surface a clean error — never an unhandled 500 crash.
    """
    create_profile_and_scope(
        "test_openai", course_key, "base/summary.json",
        slug_suffix="stream-m-openai",
        extra_llm_patch={
            "stream": True,
            "options": {"response_format": _ANSWER_SCHEMA},
        },
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code != 500, "Server crashed combining streaming + response_format"
    assert response.status_code in (200, 400, 422)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_streaming_with_response_format_anthropic_clean_outcome(live_api_client, course_key):
    """
    Anthropic does not support strict json_schema + streaming in all versions.
    The plugin must return a clean error or degrade gracefully — never a 500.
    """
    create_profile_and_scope(
        "test_anthropic", course_key, "base/summary.json",
        slug_suffix="stream-m-anthropic",
        extra_llm_patch={
            "stream": True,
            "options": {"response_format": _ANSWER_SCHEMA},
        },
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code != 500, (
        "Server crashed (500) combining streaming + response_format on Anthropic"
    )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_healthy_stream_has_no_error_marker(
    provider_slug, env_var, live_api_client, course_key
):
    """
    A normal successful streaming call must NOT contain the
    '||{"error_in_stream": true, ...}||' sentinel injected on failures.
    Its presence in a healthy stream indicates a false positive or bug.
    """
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="stream-ai",
        extra_llm_patch={"stream": True},
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code == 200
    content = _drain_stream(response)
    assert "error_in_stream" not in content, (
        f"Healthy stream contains error marker: {content[:300]}"
    )
    assert len(content) > 10, "Expected non-trivial streamed content"
