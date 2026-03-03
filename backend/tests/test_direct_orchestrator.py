"""
Tests for direct_orchestrator.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope
from openedx_ai_extensions.workflows.orchestrators.direct_orchestrator import EducatorAssistantOrchestrator, json_to_olx

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    return User.objects.create_user(
        username="educator_test_user",
        email="educator@example.com",
        password="password123",
    )


@pytest.fixture
def course_key():
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    return AIWorkflowProfile.objects.create(
        slug="test-educator-assistant",
        description="Educator assistant profile for tests",
        base_filepath="base/library_questions_assistant.json",
        content_patch="{}",
    )


@pytest.fixture
def workflow_scope(workflow_profile, course_key):  # pylint: disable=redefined-outer-name
    return AIWorkflowScope.objects.create(
        location_regex=".*test_unit.*",
        course_id=course_key,
        service_variant="cms",
        profile=workflow_profile,
        enabled=True,
    )


@pytest.fixture
def educator_orchestrator(workflow_scope, user, course_key):  # pylint: disable=redefined-outer-name
    """Instantiate EducatorAssistantOrchestrator with a real DB session."""
    context = {
        "course_id": str(course_key),
        "location_id": None,
    }
    return EducatorAssistantOrchestrator(
        workflow=workflow_scope,
        user=user,
        context=context,
    )


# ===========================================================================
# EducatorAssistantOrchestrator.get_current_session_response  (lines 98-101)
# ===========================================================================


@pytest.mark.django_db
def test_get_current_session_response_with_collection_url(
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When the session metadata already contains a collection_url,
    get_current_session_response should return it.
    """
    educator_orchestrator.session.metadata = {
        "collection_url": "authoring/library/lib:test:lib/collection/key-123"
    }
    result = educator_orchestrator.get_current_session_response(None)
    assert result == {"response": "authoring/library/lib:test:lib/collection/key-123"}


@pytest.mark.django_db
def test_get_current_session_response_no_collection_url(
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When there is no collection_url in metadata, the response value should be None.
    """
    educator_orchestrator.session.metadata = {}
    result = educator_orchestrator.get_current_session_response(None)
    assert result == {"response": None}


@pytest.mark.django_db
def test_get_current_session_response_no_metadata(
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When session metadata is None/falsy, the response value should be None.
    """
    educator_orchestrator.session.metadata = None
    result = educator_orchestrator.get_current_session_response(None)
    assert result == {"response": None}


# ===========================================================================
# EducatorAssistantOrchestrator.run — OpenEdXProcessor error  (line 114)
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
def test_educator_orchestrator_run_openedx_error(
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When OpenEdXProcessor.process returns an error dict, run() should propagate it.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"error": "Course unit not found"}
    mock_openedx_class.return_value = mock_openedx

    result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 3})

    assert "error" in result
    assert result["error"] == "Course unit not found"
    assert result["status"] == "OpenEdXProcessor error"


# ===========================================================================
# EducatorAssistantOrchestrator.run — LLM processor error  (lines 133-142)
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_educator_orchestrator_run_llm_error(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When EducatorAssistantProcessor.process returns an error, run() returns an LLM error.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "Some course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {"error": "AI API failed"}
    mock_llm_class.return_value = mock_llm

    result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 3})

    assert "error" in result
    assert result["error"] == "AI API failed"
    assert result["status"] == "LLMProcessor error"


# ===========================================================================
# EducatorAssistantOrchestrator.run — json_to_olx exception is swallowed (line 142)
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.ContentLibraryProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.json_to_olx")
def test_educator_orchestrator_run_json_to_olx_exception_is_swallowed(
    mock_json_to_olx,
    mock_library_class,
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    If json_to_olx raises an exception for a problem, that problem is skipped
    and the workflow continues with any successfully converted items.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {
            "collection_name": "Test Collection",
            "problems": [{"problem_type": "bad_type"}],
        },
        "tokens_used": 100,
        "model_used": "openai/gpt-4",
    }
    mock_llm_class.return_value = mock_llm

    mock_json_to_olx.side_effect = ValueError("conversion failed")

    mock_library = Mock()
    mock_library.create_collection_and_add_items.return_value = "collection-key-abc"
    mock_library_class.return_value = mock_library

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 1})

    assert result["status"] == "completed"
    # items list was empty because json_to_olx raised, but workflow still finished
    mock_library.create_collection_and_add_items.assert_called_once_with(
        title="Test Collection",
        description="AI-generated quiz questions",
        items=[],
    )


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.ContentLibraryProcessor")
def test_educator_orchestrator_run_success(
    mock_library_class,
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    Full success path: session metadata is updated and a completed status is returned.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {
            "collection_name": "My Quiz",
            "problems": [
                {
                    "display_name": "Q1",
                    "question_html": "What is 2+2?",
                    "problem_type": "numericalresponse",
                    "choices": [],
                    "answer_value": "4",
                    "tolerance": "0",
                    "explanation": "Basic arithmetic.",
                    "demand_hints": ["Think addition"],
                }
            ],
        },
        "tokens_used": 200,
        "model_used": "openai/gpt-4",
    }
    mock_llm_class.return_value = mock_llm

    mock_library = Mock()
    mock_library.create_collection_and_add_items.return_value = "collection-xyz"
    mock_library_class.return_value = mock_library

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 1})

    assert result["status"] == "completed"
    assert "lib:test:lib" in result["response"]
    assert "collection-xyz" in result["response"]
    assert educator_orchestrator.session.metadata["collection_id"] == "collection-xyz"


# ===========================================================================
# json_to_olx  (lines 186-244)
# ===========================================================================

COMMON_DEMAND_HINTS = ["Hint 1", "Hint 2"]


def _make_choice(text, is_correct, feedback=""):
    return {"text": text, "is_correct": is_correct, "feedback": feedback}


def test_json_to_olx_returns_dict_with_category_and_data():
    """Return value must have 'category' == 'problem' and a non-empty 'data' string."""
    problem = {
        "display_name": "Simple MCQ",
        "question_html": "Pick one",
        "problem_type": "multiplechoiceresponse",
        "choices": [_make_choice("A", True, "Correct!"), _make_choice("B", False, "Wrong")],
        "answer_value": "",
        "tolerance": "",
        "explanation": "A is correct.",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    assert result["category"] == "problem"
    assert isinstance(result["data"], str)
    assert len(result["data"]) > 0


def test_json_to_olx_multiplechoiceresponse_with_feedback_and_hints():
    """
    multiplechoiceresponse uses <choicegroup> / <choice> / <choicehint>.
    Demand hints produce a <demandhint> block.
    """
    problem = {
        "display_name": "MCQ Question",
        "question_html": "<b>What colour is the sky?</b>",
        "problem_type": "multiplechoiceresponse",
        "choices": [
            _make_choice("Blue", True, "Yes, blue!"),
            _make_choice("Red", False, "Not red."),
        ],
        "answer_value": "",
        "tolerance": "",
        "explanation": "The sky is blue.",
        "demand_hints": COMMON_DEMAND_HINTS,
    }
    result = json_to_olx(problem)
    data = result["data"]

    assert "multiplechoiceresponse" in data
    assert "choicegroup" in data
    assert "choicehint" in data
    assert "Blue" in data
    assert "Red" in data
    assert "Yes, blue!" in data
    assert "The sky is blue." in data
    assert "demandhint" in data
    assert "Hint 1" in data


def test_json_to_olx_multiplechoiceresponse_choice_without_feedback():
    """Choices with no feedback should not emit a <choicehint> tag."""
    problem = {
        "display_name": "No Feedback MCQ",
        "question_html": "Choose:",
        "problem_type": "multiplechoiceresponse",
        "choices": [_make_choice("Alpha", True, ""), _make_choice("Beta", False, "")],
        "answer_value": "",
        "tolerance": "",
        "explanation": "Alpha wins.",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    assert "choicehint" not in result["data"]


def test_json_to_olx_choiceresponse_uses_checkboxgroup():
    """choiceresponse (checkboxes) should use <checkboxgroup> inner tag."""
    problem = {
        "display_name": "Checkbox Q",
        "question_html": "Select all that apply:",
        "problem_type": "choiceresponse",
        "choices": [
            _make_choice("Option A", True, "Correct"),
            _make_choice("Option B", True, "Also correct"),
            _make_choice("Option C", False, "Wrong"),
        ],
        "answer_value": "",
        "tolerance": "",
        "explanation": "A and B are correct.",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    data = result["data"]

    assert "choiceresponse" in data
    assert "checkboxgroup" in data
    assert "Option A" in data
    assert "Also correct" in data


def test_json_to_olx_optionresponse_uses_optioninput_and_optionhint():
    """optionresponse (dropdown) should use <optioninput> / <option> / <optionhint>."""
    problem = {
        "display_name": "Dropdown Q",
        "question_html": "Pick one from dropdown:",
        "problem_type": "optionresponse",
        "choices": [
            _make_choice("Choice X", True, "X is right"),
            _make_choice("Choice Y", False, "Y is wrong"),
        ],
        "answer_value": "",
        "tolerance": "",
        "explanation": "X is the answer.",
        "demand_hints": ["Try X"],
    }
    result = json_to_olx(problem)
    data = result["data"]

    assert "optionresponse" in data
    assert "optioninput" in data
    assert "optionhint" in data
    assert "Choice X" in data
    assert "X is right" in data
    assert "Try X" in data


def test_json_to_olx_numericalresponse_with_tolerance():
    """numericalresponse with a non-empty tolerance emits a <responseparam> tag."""
    problem = {
        "display_name": "Numerical Q",
        "question_html": "What is the speed of light (approx km/s)?",
        "problem_type": "numericalresponse",
        "choices": [],
        "answer_value": "300000",
        "tolerance": "5%",
        "explanation": "~300,000 km/s",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    data = result["data"]

    assert "numericalresponse" in data
    assert "300000" in data
    assert "responseparam" in data
    assert "5%" in data
    assert "formulaequationinput" in data


def test_json_to_olx_numericalresponse_without_tolerance():
    """numericalresponse with empty tolerance should NOT emit <responseparam>."""
    problem = {
        "display_name": "Numerical No Tolerance",
        "question_html": "How many days in a week?",
        "problem_type": "numericalresponse",
        "choices": [],
        "answer_value": "7",
        "tolerance": "",
        "explanation": "7 days.",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    data = result["data"]

    assert "numericalresponse" in data
    assert "7" in data
    assert "responseparam" not in data


def test_json_to_olx_numericalresponse_unknown_tolerance_skipped():
    """'<UNKNOWN>' tolerance value must be treated like empty — no <responseparam>."""
    problem = {
        "display_name": "Unknown Tolerance",
        "question_html": "Some numeric question",
        "problem_type": "numericalresponse",
        "choices": [],
        "answer_value": "42",
        "tolerance": "<UNKNOWN>",
        "explanation": "42.",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    assert "responseparam" not in result["data"]


def test_json_to_olx_stringresponse():
    """stringresponse should use <stringresponse> / <label> / <textline>."""
    problem = {
        "display_name": "Text Input Q",
        "question_html": "Name the capital of France.",
        "problem_type": "stringresponse",
        "choices": [],
        "answer_value": "Paris",
        "tolerance": "",
        "explanation": "Paris is the capital of France.",
        "demand_hints": ["It starts with P"],
    }
    result = json_to_olx(problem)
    data = result["data"]

    assert "stringresponse" in data
    assert "Paris" in data
    assert "textline" in data
    assert "label" in data
    assert "It starts with P" in data


def test_json_to_olx_no_demand_hints_produces_no_demandhint_block():
    """When demand_hints is empty/missing, no <demandhint> tag should appear."""
    problem = {
        "display_name": "No Hints",
        "question_html": "Simple question",
        "problem_type": "stringresponse",
        "choices": [],
        "answer_value": "answer",
        "tolerance": "",
        "explanation": "explanation",
        "demand_hints": [],
    }
    result = json_to_olx(problem)
    assert "demandhint" not in result["data"]
