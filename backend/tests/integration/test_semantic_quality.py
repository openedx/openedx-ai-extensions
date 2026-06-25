"""
Semantic / quality checks (LLM-as-judge extensions).

Uses a second LLM call as an evaluator to verify that the primary response
meets language, grounding, completeness, instruction-following, and tone
requirements.
"""

import json
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from django.urls import reverse

from .conftest import PROVIDERS, create_profile_and_scope, skip_if_no_key
from .judge import COMPLETENESS, GROUNDING, INSTRUCTION_FOLLOWING, LANGUAGE_MATCH, TONE, Judge

OPENEDX_PATCH = (
    "openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process"
)


CONTEXT_JSON = json.dumps({
    "courseId": "course-v1:edX+LiveTest+Demo_Course",
    "locationId": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "uiSlotSelectorId": "live-test-slot",
})

_XFAIL_JUDGE_REASONING = pytest.mark.xfail(
    strict=False,
    reason=(
        "LLM-as-judge verdict depends on the target model's reasoning quality; "
        "weaker-reasoning providers can fail this check on an otherwise-correct "
        "response. Non-blocking per ADR 0011."
    ),
)


def _post_workflow(client, provider_slug, course_key, content, *, instruction, slug_suffix):
    """
    Run the workflow endpoint with *content* as the OpenEdX block content and
    *instruction* as the explicit prompt handed to the primary LLM.

    The instruction is the question/task the test poses, declared as a constant
    right next to its content. The same value is what each test passes to the
    judge as the INSTRUCTION leg, so the model under test and the evaluator are
    looking at exactly the same ask — no hidden, captured system role.
    """
    create_profile_and_scope(
        provider_slug, course_key, "base/custom_prompt.json",
        slug_suffix=slug_suffix, extra_llm_patch={"prompt": instruction},
    )
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    qs = urlencode({"context": CONTEXT_JSON})
    with patch(OPENEDX_PATCH, return_value=content):
        return client.post(
            f"{url}?{qs}",
            data=json.dumps({"action": "run", "user_input": {}}),
            content_type="application/json",
        )


_SPANISH_CONTENT = json.dumps({
    "unit_id": "block-v1:edX+LiveTest+Demo_Course+type@vertical+block@live_unit_001",
    "display_name": "El ciclo del agua",
    "category": "unit",
    "blocks": [
        {
            "type": "html",
            "text": (
                "El ciclo del agua describe el movimiento continuo del agua en la "
                "Tierra. Las etapas principales son la evaporación, la condensación, "
                "la precipitación y la recolección. La energía solar impulsa todo "
                "el ciclo."
            ),
        }
    ],
})

# Instruction is intentionally written in English while the content is Spanish:
# the response must follow the content's language, not the instruction's.
_SPANISH_INSTRUCTION = "Provide a brief summary of this unit for a student."


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@_XFAIL_JUDGE_REASONING
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
        _SPANISH_CONTENT, instruction=_SPANISH_INSTRUCTION, slug_suffix="qual-af",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdicts = Judge().ask(
        [LANGUAGE_MATCH], content=_SPANISH_CONTENT,
        instruction=_SPANISH_INSTRUCTION, response=llm_text,
    )
    verdict = verdicts[LANGUAGE_MATCH.name]
    assert verdict["verdict"] == "yes", (
        f"Judge ruled '{verdict}': response language does not match content language.\n"
        f"Content (Spanish): {_SPANISH_CONTENT[:100]}\n"
        f"Response: {llm_text[:200]}"
    )


_NARROW_CONTENT = (
    "The planet Zorblax orbits a red dwarf star called Velmion. "
    "Zorblax has exactly three moons named Alpha, Beta, and Gamma. "
    "The surface temperature is always exactly 42 degrees Celsius."
)

_NARROW_INSTRUCTION = "Summarize the key facts about this planet."


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@_XFAIL_JUDGE_REASONING
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
        _NARROW_CONTENT, instruction=_NARROW_INSTRUCTION, slug_suffix="qual-ag",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdicts = Judge().ask(
        [GROUNDING], content=_NARROW_CONTENT,
        instruction=_NARROW_INSTRUCTION, response=llm_text,
    )
    verdict = verdicts[GROUNDING.name]
    assert verdict["verdict"] == "yes", (
        f"Judge detected hallucination ({verdict}).\n"
        f"Content: {_NARROW_CONTENT}\n"
        f"Response: {llm_text[:300]}"
    )


_JUPITER_CONTENT = (
    "Jupiter has four large moons known as the Galilean moons: Io, Europa, "
    "Ganymede, and Callisto. They were first observed by Galileo Galilei in 1610. "
    "Io is the most volcanically active body in the solar system."
)

_JUPITER_INSTRUCTION = "Summarize what this unit says about Jupiter's moons."


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@_XFAIL_JUDGE_REASONING
def test_response_does_not_use_outside_knowledge_for_real_content(
    provider_slug, env_var, live_api_client, course_key
):
    """
    With real-world content the LLM likely has training knowledge about
    (Jupiter's moons), the response must stick to what the CONTENT says and
    not pull in related facts it knows but that aren't present here (e.g.
    Saturn's moons, Venus's atmosphere). LLM-as-judge evaluates grounding.
    """
    skip_if_no_key(env_var)

    response = _post_workflow(
        live_api_client, provider_slug, course_key,
        _JUPITER_CONTENT, instruction=_JUPITER_INSTRUCTION, slug_suffix="qual-ah2",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdicts = Judge().ask(
        [GROUNDING], content=_JUPITER_CONTENT,
        instruction=_JUPITER_INSTRUCTION, response=llm_text,
    )
    verdict = verdicts[GROUNDING.name]
    assert verdict["verdict"] == "yes", (
        f"Judge detected outside-knowledge contamination ({verdict}).\n"
        f"Content: {_JUPITER_CONTENT}\n"
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

_LIST_INSTRUCTION = "List every step of the recipe described in this content."


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@_XFAIL_JUDGE_REASONING
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
        _LIST_CONTENT, instruction=_LIST_INSTRUCTION, slug_suffix="qual-ah",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdicts = Judge().ask(
        [COMPLETENESS], content=_LIST_CONTENT,
        instruction=_LIST_INSTRUCTION, response=llm_text,
    )
    verdict = verdicts[COMPLETENESS.name]
    assert verdict["verdict"] == "yes", (
        f"Response appears truncated ({verdict}) — not all 5 steps present.\n"
        f"Response: {llm_text[:400]}"
    )


_HISTORY_CONTENT = (
    "The printing press was invented by Johannes Gutenberg around 1440. "
    "It used movable metal type and a screw-press mechanism, dramatically "
    "lowering the cost of producing books across Europe."
)

_HISTORY_INSTRUCTION = (
    "Explain this topic to a curious 10-year-old in exactly two short "
    "sentences, using a warm and encouraging tone."
)


@pytest.mark.live_llm
@pytest.mark.django_db
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
@_XFAIL_JUDGE_REASONING
def test_response_follows_instructions_and_tone(
    provider_slug, env_var, live_api_client, course_key
):
    """
    Demonstrates a single Judge.ask() call evaluating two different
    questions (instruction-following and tone) in one LLM round-trip,
    each validated against its own response_format schema.
    """
    skip_if_no_key(env_var)

    response = _post_workflow(
        live_api_client, provider_slug, course_key,
        _HISTORY_CONTENT, instruction=_HISTORY_INSTRUCTION, slug_suffix="qual-ai",
    )
    assert response.status_code == 200
    llm_text = response.json().get("response", "")
    assert llm_text, "Primary LLM returned empty response"

    verdicts = Judge().ask(
        [INSTRUCTION_FOLLOWING, TONE],
        content=_HISTORY_CONTENT,
        instruction=_HISTORY_INSTRUCTION,
        response=llm_text,
    )
    instruction_verdict = verdicts[INSTRUCTION_FOLLOWING.name]
    tone_verdict = verdicts[TONE.name]

    assert instruction_verdict["verdict"] == "yes", (
        f"Judge found unmet requirements: {instruction_verdict['missed_requirements']}\n"
        f"Response: {llm_text[:300]}"
    )
    assert tone_verdict["verdict"] == "yes", (
        f"Judge flagged a tone issue: {tone_verdict['issue']}\n"
        f"Response: {llm_text[:300]}"
    )
