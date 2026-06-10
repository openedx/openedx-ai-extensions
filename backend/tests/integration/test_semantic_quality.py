"""
Semantic / quality checks (LLM-as-judge extensions).

Uses a second LLM call as an evaluator to verify that the primary response
meets language, grounding, and completeness requirements.
"""

import json
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from .conftest import PROVIDERS, create_profile_and_scope, judge, skip_if_no_key

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)

CONTEXT_JSON = json.dumps({
    "courseId": "course-v1:edX+LiveTest+Demo_Course",
    "locationId": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "uiSlotSelectorId": "live-test-slot",
})


def _post_workflow(client, provider_slug, course_key, content, *, slug_suffix):
    """Run the workflow endpoint with *content* as the OpenEdX block content."""
    create_profile_and_scope(provider_slug, course_key, "base/summary.json", slug_suffix=slug_suffix)
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    qs = urlencode({"context": CONTEXT_JSON})
    with patch(OPENEDX_PATCH, return_value=content):
        return client.post(
            f"{url}?{qs}",
            data=json.dumps({"action": "run", "user_input": {}}),
            content_type="application/json",
        )


_SPANISH_CONTENT = (
    "El ciclo del agua describe el movimiento continuo del agua en la Tierra. "
    "Las etapas principales son la evaporación, la condensación, la precipitación "
    "y la recolección. La energía solar impulsa todo el ciclo."
)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@pytest.mark.xfail(
    strict=False,
    reason=(
        "LLM-as-judge verdict depends on the target model's reasoning quality; "
        "weaker-reasoning providers can fail this check on an otherwise-correct "
        "response. Non-blocking per ADR 0011."
    ),
)
def test_response_language_matches_content(
    provider_slug, env_var, live_api_client, course_key
):
    """
    When course content is in Spanish, the response must be in Spanish.
    No language enforcement exists in the plugin; this test catches drift.
    """
    skip_if_no_key(env_var)

    response = _post_workflow(
        live_api_client, provider_slug, course_key,
        _SPANISH_CONTENT, slug_suffix="qual-af",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdict = judge(
        system_question=(
            'Is the RESPONSE written in the same language as the CONTENT? '
            'Reply: {"verdict": "yes"} or {"verdict": "no"}'
        ),
        user_content=f"CONTENT:\n{_SPANISH_CONTENT}\n\nRESPONSE:\n{llm_text}",
    )
    assert verdict == "yes", (
        f"Judge ruled '{verdict}': response language does not match content language.\n"
        f"Content (Spanish): {_SPANISH_CONTENT[:100]}\n"
        f"Response: {llm_text[:200]}"
    )


_NARROW_CONTENT = (
    "The planet Zorblax orbits a red dwarf star called Velmion. "
    "Zorblax has exactly three moons named Alpha, Beta, and Gamma. "
    "The surface temperature is always exactly 42 degrees Celsius."
)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@pytest.mark.xfail(
    strict=False,
    reason=(
        "LLM-as-judge verdict depends on the target model's reasoning quality; "
        "weaker-reasoning providers can fail this check on an otherwise-correct "
        "response. Non-blocking per ADR 0011."
    ),
)
def test_response_does_not_hallucinate_beyond_content(
    provider_slug, env_var, live_api_client, course_key
):
    """
    With fictional, self-contained content, the response must not introduce
    facts absent from the source.  LLM-as-judge evaluates grounding.
    """
    skip_if_no_key(env_var)

    response = _post_workflow(
        live_api_client, provider_slug, course_key,
        _NARROW_CONTENT, slug_suffix="qual-ag",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdict = judge(
        system_question=(
            "Does the RESPONSE contain ONLY information that appears in the CONTENT? "
            'Reply: {"verdict": "yes"} if grounded, {"verdict": "no"} if it adds external facts.'
        ),
        user_content=f"CONTENT:\n{_NARROW_CONTENT}\n\nRESPONSE:\n{llm_text}",
    )
    assert verdict == "yes", (
        f"Judge detected hallucination (verdict='{verdict}').\n"
        f"Content: {_NARROW_CONTENT}\n"
        f"Response: {llm_text[:300]}"
    )


_LIST_CONTENT = (
    "A complete recipe requires exactly five steps: "
    "1. Gather ingredients. "
    "2. Prepare the workspace. "
    "3. Mix all components. "
    "4. Cook at the right temperature. "
    "5. Serve and enjoy."
)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@pytest.mark.xfail(
    strict=False,
    reason=(
        "LLM-as-judge verdict depends on the target model's reasoning quality; "
        "weaker-reasoning providers can fail this check on an otherwise-correct "
        "response. Non-blocking per ADR 0011."
    ),
)
def test_response_not_truncated_mid_list(
    provider_slug, env_var, live_api_client, course_key
):
    """
    A prompt that asks for all 5 items from a list must receive all 5 in the
    response.  Detects token-cap truncation mid-sentence.
    """
    skip_if_no_key(env_var)

    response = _post_workflow(
        live_api_client, provider_slug, course_key,
        _LIST_CONTENT, slug_suffix="qual-ah",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdict = judge(
        system_question=(
            "Does the RESPONSE mention all five steps from the CONTENT "
            "(gather, prepare, mix, cook, serve)? "
            'Reply: {"verdict": "yes"} or {"verdict": "no"}'
        ),
        user_content=f"CONTENT:\n{_LIST_CONTENT}\n\nRESPONSE:\n{llm_text}",
    )
    assert verdict == "yes", (
        f"Response appears truncated (verdict='{verdict}') — not all 5 steps present.\n"
        f"Response: {llm_text[:400]}"
    )
