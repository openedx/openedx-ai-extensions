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
        base_filepath="base/library_questions_creator.json",
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
# EducatorAssistantOrchestrator.get_current_session_response
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
def test_get_current_session_response_with_questions(
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When session has question_slots but no collection_url, return them for review.
    """
    question_slots = [
        {"versions": [{"display_name": "Q1", "problem_type": "multiplechoiceresponse"}], "selected": 0}
    ]
    educator_orchestrator.session.metadata = {
        "question_slots": question_slots,
        "collection_name": "My Quiz",
    }
    result = educator_orchestrator.get_current_session_response(None)
    assert result == {
        "response": {
            "question_slots": question_slots,
            "collection_name": "My Quiz",
        }
    }


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
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.json_to_olx")
def test_educator_orchestrator_run_json_to_olx_exception_is_swallowed(
    mock_json_to_olx,
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    If json_to_olx raises an exception for a problem, the problem is still
    included in question_slots (without an 'olx' key) and the workflow completes.
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
    }
    mock_llm_class.return_value = mock_llm

    mock_json_to_olx.side_effect = ValueError("conversion failed")

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 1})

    assert result["status"] == "completed"
    # Problem is included in question_slots but without 'olx' since conversion failed
    slots = result["response"]["question_slots"]
    assert len(slots) == 1
    assert "olx" not in slots[0]["versions"][0]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_educator_orchestrator_run_success_with_library_id(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    Full success path: questions are stored in session metadata as question_slots
    and a completed status is returned.
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
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 1})

    assert result["status"] == "completed"
    assert result["response"]["collection_name"] == "My Quiz"
    slots = result["response"]["question_slots"]
    assert len(slots) == 1
    assert slots[0]["versions"][0]["display_name"] == "Q1"
    assert educator_orchestrator.session.metadata["collection_name"] == "My Quiz"


# ===========================================================================
# EducatorAssistantOrchestrator.run — iterative path (no library_id)
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.ContentLibraryProcessor")
def test_educator_orchestrator_run_no_library_id_stores_questions(
    mock_library_class,
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When no library_id is provided, run() stores questions in session metadata and
    does NOT call ContentLibraryProcessor.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    problems = [
        {
            "display_name": "Q1",
            "question_html": "Question text",
            "problem_type": "multiplechoiceresponse",
            "choices": [{"text": "A", "is_correct": True, "feedback": ""}],
            "answer_value": "",
            "tolerance": "",
            "explanation": "A is correct.",
            "demand_hints": [],
        }
    ]
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {
            "collection_name": "Iterative Quiz",
            "problems": problems,
        },
    }
    mock_llm.get_usage.return_value = None
    mock_llm_class.return_value = mock_llm

    result = educator_orchestrator.run({"num_questions": 1})

    assert result["status"] == "completed"
    assert "question_slots" in result["response"]
    assert result["response"]["collection_name"] == "Iterative Quiz"
    # Each problem is wrapped in a slot with versions list and selected index
    slots = result["response"]["question_slots"]
    assert len(slots) == len(problems)
    for slot, problem in zip(slots, problems):
        assert slot["selected"] == 0
        assert len(slot["versions"]) == 1
        # The version contains the original problem fields (plus possibly 'olx')
        for key, value in problem.items():
            assert slot["versions"][0][key] == value
    # Session metadata uses question_slots
    assert "question_slots" in educator_orchestrator.session.metadata
    assert educator_orchestrator.session.metadata["collection_name"] == "Iterative Quiz"
    # ContentLibraryProcessor was NOT called
    mock_library_class.assert_not_called()


# ===========================================================================
# EducatorAssistantOrchestrator.regenerate_question
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_replaces_correct_index(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    regenerate_question() replaces the question at the specified index in session metadata.
    """
    original_questions = [
        {"display_name": "Q1", "problem_type": "multiplechoiceresponse"},
        {"display_name": "Q2", "problem_type": "stringresponse"},
    ]
    educator_orchestrator.session.metadata = {
        "question_slots": [
            {"versions": [original_questions[0]], "selected": 0},
            {"versions": [original_questions[1]], "selected": 0},
        ],
        "collection_name": "Test Quiz",
    }

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    new_question = {"display_name": "Q1-new", "problem_type": "multiplechoiceresponse"}
    mock_llm = Mock()
    mock_llm.refine_quiz_question.return_value = {
        "response": {"problems": [new_question]},
    }
    mock_llm_class.return_value = mock_llm

    result = educator_orchestrator.regenerate_question({"question_index": 0})

    assert result["status"] == "completed"
    # Response includes the new question, full version history, and selected index
    assert result["response"]["question"]["display_name"] == "Q1-new"
    assert result["response"]["selected"] == 1
    assert len(result["response"]["history"]) == 2
    # Session metadata is updated with versioned slots
    updated_slots = educator_orchestrator.session.metadata["question_slots"]
    assert updated_slots[0]["selected"] == 1
    assert len(updated_slots[0]["versions"]) == 2
    assert updated_slots[1]["versions"][0] == original_questions[1]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_openedx_error(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """regenerate_question() propagates OpenEdXProcessor errors."""
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"error": "content fetch failed"}
    mock_openedx_class.return_value = mock_openedx

    result = educator_orchestrator.regenerate_question({"question_index": 0})

    assert "error" in result
    assert result["status"] == "OpenEdXProcessor error"
    mock_llm_class.assert_not_called()


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_invalid_index_returns_error(
    mock_llm_class,  # pylint: disable=unused-argument
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    regenerate_question() returns an error when question_index is out of range.
    """
    educator_orchestrator.session.metadata = {
        "question_slots": [
            {"versions": [{"display_name": "Q1"}], "selected": 0},
        ],
        "collection_name": "Quiz",
    }

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    result = educator_orchestrator.regenerate_question({"question_index": 5})

    assert result["status"] == "error"
    assert result["error"] == "Invalid question index"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_none_index_returns_error(
    mock_llm_class,  # pylint: disable=unused-argument
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    regenerate_question() returns an error when question_index is None.
    """
    educator_orchestrator.session.metadata = {
        "question_slots": [
            {"versions": [{"display_name": "Q1"}], "selected": 0},
        ],
    }

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    result = educator_orchestrator.regenerate_question({})

    assert result["status"] == "error"
    assert result["error"] == "Invalid question index"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_llm_error(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    regenerate_question() propagates LLM errors when refine_quiz_question fails.
    """
    educator_orchestrator.session.metadata = {
        "question_slots": [
            {"versions": [{"display_name": "Q1"}], "selected": 0},
        ],
        "collection_name": "Quiz",
    }

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.refine_quiz_question.return_value = {"error": "LLM timeout"}
    mock_llm_class.return_value = mock_llm

    result = educator_orchestrator.regenerate_question({"question_index": 0})

    assert result["status"] == "LLMProcessor error"
    assert result["error"] == "LLM timeout"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_empty_problems_returns_error(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    regenerate_question() returns an error when LLM returns no problems.
    """
    educator_orchestrator.session.metadata = {
        "question_slots": [
            {"versions": [{"display_name": "Q1"}], "selected": 0},
        ],
        "collection_name": "Quiz",
    }

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.refine_quiz_question.return_value = {
        "response": {"problems": []},
    }
    mock_llm_class.return_value = mock_llm

    result = educator_orchestrator.regenerate_question({"question_index": 0})

    assert result["status"] == "error"
    assert result["error"] == "No question generated"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_regenerate_question_appends_version_history(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    Multiple regenerations append to the versions list and update selected.
    """
    original = {"display_name": "Q1", "problem_type": "multiplechoiceresponse"}
    educator_orchestrator.session.metadata = {
        "question_slots": [
            {"versions": [original], "selected": 0},
        ],
        "collection_name": "Quiz",
    }

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    v2 = {"display_name": "Q1-v2", "problem_type": "multiplechoiceresponse"}
    mock_llm = Mock()
    mock_llm.refine_quiz_question.return_value = {
        "response": {"problems": [v2]},
    }
    mock_llm_class.return_value = mock_llm

    # First regeneration
    result1 = educator_orchestrator.regenerate_question({"question_index": 0})
    assert result1["status"] == "completed"
    assert result1["response"]["selected"] == 1
    assert len(result1["response"]["history"]) == 2

    # Second regeneration
    v3 = {"display_name": "Q1-v3", "problem_type": "multiplechoiceresponse"}
    mock_llm.refine_quiz_question.return_value = {
        "response": {"problems": [v3]},
    }

    result2 = educator_orchestrator.regenerate_question({"question_index": 0})
    assert result2["status"] == "completed"
    assert result2["response"]["selected"] == 2
    assert len(result2["response"]["history"]) == 3

    # All versions are in session metadata
    slot = educator_orchestrator.session.metadata["question_slots"][0]
    assert slot["versions"][0] == original
    assert slot["versions"][1]["display_name"] == "Q1-v2"
    assert slot["versions"][2]["display_name"] == "Q1-v3"
    assert slot["selected"] == 2


# ===========================================================================
# EducatorAssistantOrchestrator.run — stores metadata in session
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_run_with_library_id_stores_metadata_and_emits_event(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When run() completes, session metadata stores question_slots and
    collection_name for iterative review.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {
            "collection_name": "Legacy Quiz",
            "problems": [
                {
                    "display_name": "Q1",
                    "question_html": "What is 1+1?",
                    "problem_type": "numericalresponse",
                    "choices": [],
                    "answer_value": "2",
                    "tolerance": "",
                    "explanation": "Basic math.",
                    "demand_hints": [],
                }
            ],
        },
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(educator_orchestrator, "_emit_workflow_event") as _:
        result = educator_orchestrator.run({"library_id": "lib:org:mylib", "num_questions": 1})

    assert result["status"] == "completed"
    assert result["response"]["collection_name"] == "Legacy Quiz"
    assert len(result["response"]["question_slots"]) == 1

    # Session metadata stores question_slots and collection_name
    meta = educator_orchestrator.session.metadata
    assert meta["collection_name"] == "Legacy Quiz"
    assert len(meta["question_slots"]) == 1
    assert meta["question_slots"][0]["versions"][0]["display_name"] == "Q1"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_run_with_library_id_empty_problems_list(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When LLM returns an empty problems list, question_slots is empty and
    the workflow completes.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {
            "collection_name": "Empty Quiz",
            "problems": [],
        },
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 0})

    assert result["status"] == "completed"
    assert result["response"]["question_slots"] == []
    assert result["response"]["collection_name"] == "Empty Quiz"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.EducatorAssistantProcessor")
def test_run_with_library_id_multiple_problems_converted(
    mock_llm_class,
    mock_openedx_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    All problems are stored in question_slots for iterative review.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    problems = [
        {
            "display_name": f"Q{i}",
            "question_html": f"Question {i}",
            "problem_type": "stringresponse",
            "choices": [],
            "answer_value": f"Answer{i}",
            "tolerance": "",
            "explanation": f"Explanation {i}.",
            "demand_hints": [],
        }
        for i in range(3)
    ]

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {
            "collection_name": "Multi Quiz",
            "problems": problems,
        },
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.run({"library_id": "lib:test:lib", "num_questions": 3})

    assert result["status"] == "completed"
    # All 3 problems are stored in question_slots
    assert len(result["response"]["question_slots"]) == 3


# ===========================================================================
# EducatorAssistantOrchestrator.save
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.ContentLibraryProcessor")
def test_save_converts_questions_and_calls_library(
    mock_library_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    save() converts questions to OLX, calls ContentLibraryProcessor, stores
    collection_url in metadata, and returns it.
    """
    educator_orchestrator.session.metadata = {"collection_name": "Review Quiz"}

    questions = [
        {
            "display_name": "Q1",
            "question_html": "Pick one",
            "problem_type": "multiplechoiceresponse",
            "choices": [{"text": "A", "is_correct": True, "feedback": ""}],
            "answer_value": "",
            "tolerance": "",
            "explanation": "A is correct.",
            "demand_hints": [],
        }
    ]

    mock_library = Mock()
    mock_library.create_collection_and_add_items.return_value = "new-collection-key"
    mock_library_class.return_value = mock_library

    with patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.save({
            "library_id": "lib:test:lib",
            "questions": questions,
        })

    assert result["status"] == "completed"
    assert "lib:test:lib" in result["response"]
    assert "new-collection-key" in result["response"]
    mock_library.create_collection_and_add_items.assert_called_once_with(
        title="Review Quiz",
        description="AI-generated quiz questions",
        items=mock_library.create_collection_and_add_items.call_args.kwargs["items"],
    )
    assert educator_orchestrator.session.metadata["collection_url"] == result["response"]
    assert educator_orchestrator.session.metadata["collection_id"] == "new-collection-key"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.ContentLibraryProcessor")
def test_save_skips_bad_questions(
    mock_library_class,
    educator_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    save() swallows json_to_olx conversion errors and continues with valid items.
    """
    educator_orchestrator.session.metadata = {"collection_name": "Quiz"}

    mock_library = Mock()
    mock_library.create_collection_and_add_items.return_value = "ck"
    mock_library_class.return_value = mock_library

    with patch(
        "openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.json_to_olx",
        side_effect=ValueError("bad"),
    ), patch.object(educator_orchestrator, "_emit_workflow_event"):
        result = educator_orchestrator.save({
            "library_id": "lib:test:lib",
            "questions": [{"problem_type": "unknown"}],
        })

    assert result["status"] == "completed"
    mock_library.create_collection_and_add_items.assert_called_once_with(
        title="Quiz",
        description="AI-generated quiz questions",
        items=[],
    )


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
