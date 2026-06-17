"""
Response format depth.

Verifies that schema constraints (additionalProperties, minItems) declared
in a json_schema response_format are enforced by the provider.
"""

import json
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from .conftest import PROVIDERS, create_profile_and_scope, skip_if_no_key
from .sample_schemas import ARRAY_SCHEMA, FLASHCARDS_SCHEMA

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)

DUMMY_CONTENT = (
    "The water cycle describes the continuous movement of water on, above, "
    "and below Earth's surface. The main stages are evaporation, condensation, "
    "precipitation, and collection. Solar energy drives the process."
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


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_response_format_no_extra_keys(
    provider_slug, env_var, live_api_client, course_key
):
    """
    When schema declares additionalProperties: false, the parsed response
    must contain ONLY the declared keys — no extras injected by the LLM.
    """
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="fmt-s",
        extra_llm_patch={"options": {"response_format": FLASHCARDS_SCHEMA}},
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed", f"Unexpected status: {data}"

    parsed = json.loads(data["response"])
    extra_keys = set(parsed.keys()) - {"cards"}
    assert not extra_keys, (
        f"LLM returned keys not in schema: {extra_keys}. Full response: {parsed}"
    )
    cards = parsed.get("cards", [])
    assert cards, "Expected at least one flashcard"
    for card in cards:
        card_extra_keys = set(card.keys()) - {"id", "question", "answer"}
        assert not card_extra_keys, (
            f"Flashcard returned keys not in schema: {card_extra_keys}. Card: {card}"
        )


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_response_format_required_array_non_empty(
    provider_slug, env_var, live_api_client, course_key
):
    """
    When schema declares minItems: 1 on a required array, the LLM must
    return at least one element — an empty list violates the schema.
    """
    skip_if_no_key(env_var)
    create_profile_and_scope(
        provider_slug, course_key, "base/summary.json",
        slug_suffix="fmt-t",
        extra_llm_patch={"options": {"response_format": ARRAY_SCHEMA}},
    )

    with patch(OPENEDX_PATCH, return_value=DUMMY_CONTENT):
        response = _post_workflow(live_api_client)

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "completed", f"Unexpected status: {data}"

    parsed = json.loads(data["response"])
    items = parsed.get("items", [])
    assert len(items) >= 1, (
        f"LLM returned empty items array despite minItems:1 in schema. Got: {parsed}"
    )
    assert all(isinstance(i, str) for i in items), f"All items must be strings. Got: {items}"
