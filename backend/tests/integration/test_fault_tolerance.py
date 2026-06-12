"""
Fault tolerance & API rejections.

Verifies that auth failures and bad model names are surfaced cleanly
without unhandled exceptions reaching the test runner.
"""

import json
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from .conftest import INVALID_CREDENTIALS, PROVIDERS, create_profile_and_scope, skip_if_no_key
from .sample_content import SAMPLE_UNIT_CONTENT

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)

CONTEXT_JSON = json.dumps({
    "courseId": "course-v1:edX+LiveTest+Demo_Course",
    "locationId": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "uiSlotSelectorId": "live-test-slot",
})


def _post_workflow(client):
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    qs = urlencode({"context": CONTEXT_JSON})
    return client.post(
        f"{url}?{qs}",
        data=json.dumps({"action": "run", "user_input": {}}),
        content_type="application/json",
    )


def _assert_error_surfaced(response):
    """
    Accept any failure signal: HTTP 4xx/5xx, or a 200 body that does NOT
    claim status='completed'. Streaming responses are also checked.
    """
    if response.status_code == 200:
        # Non-streaming JSON path
        try:
            body = response.json()
            assert body.get("status") != "completed", (
                f"Got unexpected status='completed': {body}"
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # Streaming path — drain and look for error signal
            content = b"".join(response.streaming_content).decode("utf-8")
            assert "error" in content.lower() or "error_in_stream" in content, (
                f"Streaming response had no error signal: {content[:200]}"
            )
    else:
        assert response.status_code >= 400, (
            f"Expected 4xx/5xx, got {response.status_code}"
        )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_invalid_api_key_does_not_return_completed(
    provider_slug, env_var, live_api_client, course_key
):
    """
    A deliberately wrong API key must surface an error, not silently
    return status='completed'.
    """
    skip_if_no_key(env_var)

    bad_key = INVALID_CREDENTIALS[provider_slug]["bad_key"]

    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="bad-key",
        extra_llm_patch={"options": {"api_key": bad_key}},
    )

    with patch(OPENEDX_PATCH, return_value=SAMPLE_UNIT_CONTENT):
        response = _post_workflow(live_api_client)

    _assert_error_surfaced(response)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_wrong_model_name_does_not_return_completed(
    provider_slug, env_var, live_api_client, course_key
):
    """
    A non-existent model name must surface an error, not produce a
    'completed' response with placeholder text.
    """
    skip_if_no_key(env_var)

    bad_model = INVALID_CREDENTIALS[provider_slug]["bad_model"]

    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="bad-model",
        extra_llm_patch={"options": {"model": bad_model}},
    )

    with patch(OPENEDX_PATCH, return_value=SAMPLE_UNIT_CONTENT):
        response = _post_workflow(live_api_client)

    _assert_error_surfaced(response)
