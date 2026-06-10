"""
Profile coverage tests.

Exercises profiles not covered by the primary test suite by sending real
HTTP requests through the full orchestrator → processor → LLM chain.
"""

import json
import os
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope

from .conftest import PROVIDERS, create_profile_and_scope, skip_if_no_key

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)

DUMMY_CONTENT = (
    "Photosynthesis is the process by which plants convert light energy into "
    "chemical energy stored in glucose. Chlorophyll, found in chloroplasts, "
    "absorbs sunlight. The reaction combines carbon dioxide and water to produce "
    "glucose and oxygen. This process is fundamental to life on Earth."
)

_CONTEXT_JSON = json.dumps({
    "courseId": "course-v1:edX+LiveTest+Demo_Course",
    "locationId": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "uiSlotSelectorId": "live-test-slot",
})


def _post(client, user_input=None):
    """POST to the workflow endpoint with the shared dummy context and content."""
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    qs = urlencode({"context": _CONTEXT_JSON})
    body = json.dumps({"action": "run", "user_input": user_input or {}})
    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        return client.post(f"{url}?{qs}", data=body, content_type="application/json")


def _create_educator_profile_and_scope(provider_slug, course_key):
    """Like create_profile_and_scope but patches EducatorAssistantProcessor."""
    content_patch = json.dumps(
        {"processor_config": {"EducatorAssistantProcessor": {"provider": provider_slug}}}
    )
    profile = AIWorkflowProfile.objects.create(
        slug=f"live-{provider_slug}-lib-creator",
        description=f"Live integration test — {provider_slug} / library-creator",
        base_filepath="base/library_questions_creator.json",
        content_patch=content_patch,
    )
    AIWorkflowScope.objects.create(
        location_regex=r".*live_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=profile,
        enabled=True,
        ui_slot_selector_id="live-test-slot",
    )
    return profile


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_custom_prompt_profile_returns_rephrased_content(
    provider_slug, env_var, live_api_client, course_key
):
    """
    base/custom_prompt.json: call_with_custom_prompt via DirectLLMResponse
    returns a non-empty completed response using the inline prompt from the profile.
    """
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/custom_prompt.json", slug_suffix="custom-prompt"
    )
    response = _post(live_api_client)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed", f"Unexpected status: {data}"
    assert len(data.get("response", "")) > 20, f"Response too short: {data.get('response')}"


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_library_creator_profile_returns_quiz_problems(
    provider_slug, env_var, live_api_client, course_key
):
    """
    base/library_questions_creator.json: EducatorAssistantOrchestrator via the
    full HTTP stack returns a problems list with at least one well-formed item.
    """
    skip_if_no_key(env_var)
    _create_educator_profile_and_scope(provider_slug, course_key)
    response = _post(live_api_client, user_input={"num_questions": 2})
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed", f"Unexpected status: {data}"
    payload = data.get("response", {})
    if isinstance(payload, str):
        payload = json.loads(payload)
    # EducatorAssistantOrchestrator wraps LLM problems into question_slots for iterative review
    slots = payload.get("question_slots", [])
    assert len(slots) > 0, f"Expected question_slots list, got: {payload}"
    required = {"display_name", "question_html", "problem_type", "choices"}
    for i, slot in enumerate(slots):
        problem = slot.get("versions", [{}])[0]
        missing = required - set(problem.keys())
        assert not missing, f"Slot {i} problem missing fields: {missing}"


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_box_hello_profile_returns_greeting(live_api_client, course_key):
    """
    examples/openai/box_hello.json: greet_from_llm via DirectLLMResponse
    returns a non-empty response.
    """
    create_profile_and_scope(
        "test_openai", course_key, "examples/openai/box_hello.json", slug_suffix="box-hello"
    )
    response = _post(live_api_client)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed", f"Unexpected status: {data}"
    assert len(data.get("response", "")) > 10, f"Response too short: {data.get('response')}"


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_chat_profile_non_streaming_returns_response(live_api_client, course_key):
    """
    examples/openai/chat.json: ThreadedLLMResponse via the full HTTP stack
    (stream overridden to False) returns a non-empty completed response.
    """
    create_profile_and_scope(
        "test_openai", course_key, "examples/openai/chat.json", slug_suffix="chat"
    )
    response = _post(live_api_client, user_input="What is photosynthesis?")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed", f"Unexpected status: {data}"
    assert len(data.get("response", "")) > 10, f"Response too short: {data.get('response')}"
