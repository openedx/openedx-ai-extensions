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

from .conftest import PROVIDERS, skip_if_no_key

COURSE_CONTENT = (
    "The water cycle describes the continuous movement of water within Earth. "
    "It has four main stages: evaporation (water turns to vapour from heat), "
    "condensation (vapour cools and forms clouds), precipitation (water falls as "
    "rain or snow), and collection (water gathers in oceans, lakes, and rivers). "
    "Energy from the sun drives the whole cycle."
)

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "openedx_ai_extensions"
    / "response_schemas"
    / "educator_quiz_questions.json"
)


def _make_processor(provider_slug):
    """Instantiate EducatorAssistantProcessor with the given provider."""
    from openedx_ai_extensions.processors.llm.educator_assistant_processor import (  # pylint: disable=C0415
        EducatorAssistantProcessor,
    )

    config = {
        "EducatorAssistantProcessor": {
            "provider": provider_slug,
            "stream": False,
            "function": "generate_quiz_questions",
        }
    }
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return EducatorAssistantProcessor(
        config=config,
        context=COURSE_CONTENT,
        extra_params={"response_format": schema},
    )


@pytest.mark.live_llm
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_quiz_generation_returns_non_empty_problems(provider_slug, env_var):
    """
    LLM must return at least one quiz problem with all required fields.
    Catches the missing minItems constraint in educator_quiz_questions.json.
    """
    skip_if_no_key(env_var)

    processor = _make_processor(provider_slug)
    result = processor.process(input_data={"num_questions": 2})

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
def test_quiz_generation_response_is_valid_json(provider_slug, env_var):
    """
    Processor must complete without JSONDecodeError and return a dict response.
    The schema we control constrains the LLM to valid JSON; an unguarded
    json.loads failure surfaces naturally as a test error.
    """
    skip_if_no_key(env_var)

    processor = _make_processor(provider_slug)
    result = processor.process(input_data={"num_questions": 1})

    assert result.get("status") == "success", f"Processor failed: {result}"
    assert isinstance(result.get("response"), dict), (
        f"Expected response to be a parsed dict, got: {type(result.get('response'))}"
    )
    assert "collection_name" in result["response"], (
        f"'collection_name' missing from response: {result['response']}"
    )
