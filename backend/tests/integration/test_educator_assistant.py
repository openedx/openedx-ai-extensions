"""
EducatorAssistant & structured outputs.

Calls EducatorAssistantProcessor directly (bypassing the API) against a
real LLM to verify:
  Z  — the LLM returns a non-empty problems list
  AA — the processor returns a parsed dict response (json.loads correctness
       is verified implicitly; any JSONDecodeError surfaces as a test failure)
"""

import json
from pathlib import Path

import pytest

from openedx_ai_extensions.workflows.template_utils import get_effective_config

from .conftest import PROVIDERS, skip_if_no_key
from .sample_content import SAMPLE_UNIT_CONTENT

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "openedx_ai_extensions"
    / "response_schemas"
    / "educator_quiz_questions.json"
)


def _make_processor(provider_slug):
    """
    Instantiate EducatorAssistantProcessor from base/library_questions_creator.json,
    patched to use the given provider in non-streaming mode.
    """
    from openedx_ai_extensions.processors.llm.educator_assistant_processor import (  # pylint: disable=C0415
        EducatorAssistantProcessor,
    )

    content_patch = {
        "processor_config": {
            "EducatorAssistantProcessor": {"provider": provider_slug, "stream": False},
        }
    }
    effective_config = get_effective_config("base/library_questions_creator.json", content_patch)

    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return EducatorAssistantProcessor(
        config=effective_config["processor_config"],
        context=SAMPLE_UNIT_CONTENT,
        extra_params={"response_format": schema},
    )


_quiz_results: dict[str, dict] = {}


@pytest.fixture
def quiz_result(provider_slug, env_var):
    """
    Run quiz generation once per provider and cache the result so both
    structural checks below reuse the same LLM call (saves tokens & runtime).
    """
    skip_if_no_key(env_var)
    if provider_slug not in _quiz_results:
        processor = _make_processor(provider_slug)
        _quiz_results[provider_slug] = processor.process(input_data={"num_questions": 2})
    return _quiz_results[provider_slug]


@pytest.mark.live_llm
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_quiz_generation_returns_non_empty_problems(  # pylint: disable=unused-argument
    provider_slug, env_var, quiz_result  # pylint: disable=redefined-outer-name
):
    """
    LLM must return at least one quiz problem with all required fields.
    Catches the missing minItems constraint in educator_quiz_questions.json.
    """
    result = quiz_result

    assert result.get("status") == "success", f"Processor failed: {result}"

    payload = result.get("response", {})
    problems = payload.get("problems", [])

    assert len(problems) > 0, (
        "LLM returned an empty problems list — missing minItems enforcement"
    )

    required_fields = {"display_name", "question_html", "problem_type", "choices"}
    for i, problem in enumerate(problems):
        missing = required_fields - set(problem.keys())
        assert not missing, f"Problem {i} missing fields: {missing}\n  Got: {problem}"

    assert payload.get("collection_name"), "collection_name must be a non-empty string"


@pytest.mark.live_llm
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_quiz_generation_response_is_valid_json(  # pylint: disable=unused-argument
    provider_slug, env_var, quiz_result  # pylint: disable=redefined-outer-name
):
    """
    Processor must complete without JSONDecodeError and return a dict response.
    The schema we control constrains the LLM to valid JSON; an unguarded
    json.loads failure surfaces naturally as a test error.
    """
    result = quiz_result

    assert result.get("status") == "success", f"Processor failed: {result}"
    assert isinstance(result.get("response"), dict), (
        f"Expected response to be a parsed dict, got: {type(result.get('response'))}"
    )
    assert "collection_name" in result["response"], (
        f"'collection_name' missing from response: {result['response']}"
    )
