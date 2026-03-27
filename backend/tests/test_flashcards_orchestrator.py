"""
Tests for flashcards_orchestrator.
"""
# pylint: disable=protected-access

from unittest.mock import Mock, mock_open, patch

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope
from openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator import FlashCardsOrchestrator

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    return User.objects.create_user(
        username="flashcards_test_user",
        email="flashcards@example.com",
        password="password123",
    )


@pytest.fixture
def course_key():
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    return AIWorkflowProfile.objects.create(
        slug="test-flashcards",
        description="Flashcards profile for tests",
        base_filepath="experimental/fashcards.json",
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
def flashcards_orchestrator(workflow_scope, user, course_key):  # pylint: disable=redefined-outer-name
    """Instantiate FlashCardsOrchestrator with a real DB session."""
    context = {
        "course_id": str(course_key),
        "location_id": None,
    }
    return FlashCardsOrchestrator(
        workflow=workflow_scope,
        user=user,
        context=context,
    )


# ===========================================================================
# FlashCardsOrchestrator.get_current_session_response
# ===========================================================================


@pytest.mark.django_db
def test_get_current_session_response_with_cards(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When session metadata contains cards, get_current_session_response returns them.
    """
    cards = [
        {"id": "card-1", "question": "What is 2+2?", "answer": "4"},
        {"id": "card-2", "question": "Capital of France?", "answer": "Paris"},
    ]
    flashcards_orchestrator.session.metadata = {"cards": cards}

    result = flashcards_orchestrator.get_current_session_response(None)
    assert result == {'cards': cards, 'status': 'completed'}


@pytest.mark.django_db
def test_get_current_session_response_no_cards(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When there are no cards in metadata, returns None.
    """
    flashcards_orchestrator.session.metadata = {}

    result = flashcards_orchestrator.get_current_session_response(None)
    assert result == {'cards': None, 'status': 'no_flashcards'}


@pytest.mark.django_db
def test_get_current_session_response_none_metadata(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When session metadata is None, returns None.
    """
    flashcards_orchestrator.session.metadata = None

    result = flashcards_orchestrator.get_current_session_response(None)
    assert result == {'cards': None, 'status': 'no_flashcards'}


# ===========================================================================
# FlashCardsOrchestrator.run — OpenEdXProcessor error
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
def test_run_openedx_error(
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When OpenEdXProcessor.process returns an error dict, run() propagates it.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"error": "Course unit not found"}
    mock_openedx_class.return_value = mock_openedx

    result = flashcards_orchestrator.run({"num_cards": 5})

    assert "error" in result
    assert result["error"] == "Course unit not found"
    assert result["status"] == "OpenEdXProcessor error"


# ===========================================================================
# FlashCardsOrchestrator.run — LLMProcessor error
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_llm_error(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When LLMProcessor.process returns an error, run() returns an LLM error.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "Some course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {"error": "AI API failed"}
    mock_llm_class.return_value = mock_llm

    result = flashcards_orchestrator.run({"num_cards": 5})

    assert "error" in result
    assert result["error"] == "AI API failed"
    assert result["status"] == "LLMProcessor error"


# ===========================================================================
# FlashCardsOrchestrator.run — success path with dict response
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_success_dict_response(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    Full success path: response is a dict with 'cards' list.
    Cards should be enriched with spaced-repetition fields.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    cards = [
        {"id": "card-1", "question": "What is 2+2?", "answer": "4"},
        {"id": "card-2", "question": "Capital of France?", "answer": "Paris"},
    ]
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": cards},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 2})

    assert result["status"] == "completed"

    enriched_cards = result["response"]
    assert isinstance(enriched_cards, list)
    assert len(enriched_cards) == 2
    for card in enriched_cards:
        assert card["nextReviewTime"] == 0
        assert card["interval"] == 1
        assert card["easeFactor"] == 2.5
        assert card["repetitions"] == 0
        assert card["lastReviewedAt"] is None


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_success_emits_workflow_event(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    On success, run() emits a workflow completed event.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": []},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event") as mock_emit:
        flashcards_orchestrator.run({"num_cards": 1})

    mock_emit.assert_called_once()


# ===========================================================================
# FlashCardsOrchestrator.run — success path with list response
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_success_list_response(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When response_obj is a list (not a dict), cards are extracted directly.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    cards = [
        {"id": "card-1", "question": "Q1?", "answer": "A1"},
    ]
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": cards,
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 1})

    assert result["status"] == "completed"
    # When response is a list, enriched_response is the cards list directly
    enriched_cards = result["response"]
    assert isinstance(enriched_cards, list)
    assert len(enriched_cards) == 1
    assert enriched_cards[0]["nextReviewTime"] == 0
    assert enriched_cards[0]["easeFactor"] == 2.5


# ===========================================================================
# FlashCardsOrchestrator.run — default num_cards
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.random")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_default_num_cards(
    mock_llm_class,
    mock_openedx_class,
    mock_random,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When num_cards is not provided, a random number between 1 and 25 is generated.
    """
    mock_random.randint.return_value = 10

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": []},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        flashcards_orchestrator.run({})

    mock_random.randint.assert_called_once_with(1, 25)
    # Verify input_data was updated with the random num_cards
    call_kwargs = mock_llm.process.call_args[1]
    assert call_kwargs["input_data"]["num_cards"] == 10


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_explicit_num_cards_not_overridden(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When num_cards is explicitly provided, the random fallback is not used.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": []},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        flashcards_orchestrator.run({"num_cards": 7})

    call_kwargs = mock_llm.process.call_args[1]
    assert call_kwargs["input_data"]["num_cards"] == 7


# ===========================================================================
# FlashCardsOrchestrator.run — schema file is loaded
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_loads_schema_and_passes_response_format(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    run() loads the flashcards JSON schema and passes it as response_format to LLMProcessor.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": []},
    }
    mock_llm_class.return_value = mock_llm

    schema_data = {"type": "json_schema", "json_schema": {"name": "FlashcardGeneration"}}
    with patch.object(flashcards_orchestrator, "_emit_workflow_event"), \
         patch("builtins.open", mock_open(read_data='{"type": "json_schema"}')), \
         patch("json.load", return_value=schema_data):
        flashcards_orchestrator.run({"num_cards": 3})

    # Verify LLMProcessor was instantiated with the response_format
    call_kwargs = mock_llm_class.call_args[1]
    assert "response_format" in call_kwargs["extra_params"]
    assert call_kwargs["extra_params"]["response_format"] == schema_data


# ===========================================================================
# FlashCardsOrchestrator.run — empty cards list
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_success_empty_cards(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When LLM returns an empty cards list, run() still completes successfully.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": []},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 0})

    assert result["status"] == "completed"
    assert result["response"] == []


# ===========================================================================
# FlashCardsOrchestrator.run — response with no 'cards' key
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_dict_response_no_cards_key(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When the LLM response is a dict without a 'cards' key, it is treated as
    having no cards — the result contains an empty list.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"other_data": "value"},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 1})

    assert result["status"] == "completed"
    assert result["response"] == []


# ===========================================================================
# FlashCardsOrchestrator.run — response_obj is None
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_none_response(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When response_obj is None, cards defaults to empty list.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": None,
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 1})

    assert result["status"] == "completed"
    # None is normalized to an empty list by _get_structured_cards
    assert result["response"] == []


# ===========================================================================
# FlashCardsOrchestrator.save
# ===========================================================================


@pytest.mark.django_db
def test_save_stores_cards_in_session(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    save() stores cards in session metadata and returns flashcards_saved status.
    """
    flashcards_orchestrator.session.metadata = {}

    cards = [
        {"id": "card-1", "question": "Q1?", "answer": "A1"},
        {"id": "card-2", "question": "Q2?", "answer": "A2"},
    ]
    result = flashcards_orchestrator.save({"cards": cards})

    assert result["status"] == "saved"

    flashcards_orchestrator.session.refresh_from_db()
    assert flashcards_orchestrator.session.metadata["cards"] == cards


@pytest.mark.django_db
def test_save_stores_card_stack_fallback(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    save() falls back to 'card_stack' key when 'cards' is not present.
    """
    flashcards_orchestrator.session.metadata = {}

    card_stack = [
        {"id": "card-1", "question": "Q1?", "answer": "A1"},
    ]
    result = flashcards_orchestrator.save({"card_stack": card_stack})

    assert result["status"] == "saved"

    flashcards_orchestrator.session.refresh_from_db()
    assert flashcards_orchestrator.session.metadata["cards"] == card_stack


@pytest.mark.django_db
def test_save_prefers_cards_over_card_stack(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    save() prefers 'cards' key over 'card_stack' when both are present.
    """
    flashcards_orchestrator.session.metadata = {}

    cards = [{"id": "card-1", "question": "Q?", "answer": "A"}]
    card_stack = [{"id": "card-2", "question": "Q2?", "answer": "A2"}]
    result = flashcards_orchestrator.save({"cards": cards, "card_stack": card_stack})

    assert result["status"] == "saved"

    flashcards_orchestrator.session.refresh_from_db()
    assert flashcards_orchestrator.session.metadata["cards"] == cards


@pytest.mark.django_db
def test_save_with_no_cards_or_card_stack(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    save() stores None when neither 'cards' nor 'card_stack' are present.
    """
    flashcards_orchestrator.session.metadata = {}

    result = flashcards_orchestrator.save({})

    assert result["status"] == "saved"
    assert result["message"] == "0 cards saved successfully."

    flashcards_orchestrator.session.refresh_from_db()
    assert flashcards_orchestrator.session.metadata["cards"] is None


# ===========================================================================
# FlashCardsOrchestrator._schema_path
# ===========================================================================


def test_schema_path_points_to_flashcards_json(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    _schema_path should point to the flashcards.json schema file.
    """
    schema_path = flashcards_orchestrator._schema_path
    assert schema_path.name == "flashcards.json"
    assert "response_schemas" in str(schema_path)


# ===========================================================================
# FlashCardsOrchestrator.run — card enrichment details
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_card_enrichment_preserves_original_fields(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    Card enrichment adds spaced-repetition fields without removing original fields.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    cards = [
        {"id": "card-1", "question": "What is DNA?", "answer": "Deoxyribonucleic acid"},
    ]
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": cards},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 1})

    card = result["response"][0]
    # Original fields preserved
    assert card["id"] == "card-1"
    assert card["question"] == "What is DNA?"
    assert card["answer"] == "Deoxyribonucleic acid"
    # Spaced-repetition fields added
    assert card["nextReviewTime"] == 0
    assert card["interval"] == 1
    assert card["easeFactor"] == 2.5
    assert card["repetitions"] == 0
    assert card["lastReviewedAt"] is None


# ===========================================================================
# FlashCardsOrchestrator.run — non-dict items in cards list are skipped
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_non_dict_card_items_are_skipped(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    Non-dict items in the cards list are not enriched (no error raised).
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    cards = [
        {"id": "card-1", "question": "Q1?", "answer": "A1"},
        "not-a-dict",
        42,
    ]
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": cards},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        result = flashcards_orchestrator.run({"num_cards": 1})

    assert result["status"] == "completed"
    enriched_cards = result["response"]
    assert isinstance(enriched_cards, list)
    # Only the dict item gets enriched
    assert "nextReviewTime" in enriched_cards[0]
    assert enriched_cards[1] == "not-a-dict"
    assert enriched_cards[2] == 42


# ===========================================================================
# FlashCardsOrchestrator.run — LLMProcessor receives correct arguments
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_passes_content_and_input_data_to_llm(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    run() passes the stringified content result and input_data to LLMProcessor.process().
    """
    content_data = {"content": "Python fundamentals: variables, functions, and loops"}
    mock_openedx = Mock()
    mock_openedx.process.return_value = content_data
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": []},
    }
    mock_llm_class.return_value = mock_llm

    input_data = {"num_cards": 5}
    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        flashcards_orchestrator.run(input_data)

    call_kwargs = mock_llm.process.call_args[1]
    assert call_kwargs["context"] == str(content_data)
    assert call_kwargs["input_data"] == input_data


# ===========================================================================
# FlashCardsOrchestrator.run — existing cards are sent as context (lines 86-96)
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_existing_cards_passed_as_context(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When session already contains cards, run() builds an existing_cards string
    and includes it in input_data so the LLM avoids duplicates.
    """
    existing = [
        {"id": "card-1", "question": "What is 2+2?", "answer": "4"},
        {"id": "card-2", "question": "Capital of France?", "answer": "Paris"},
    ]
    flashcards_orchestrator.session.metadata = {"cards": existing}
    flashcards_orchestrator.session.save(update_fields=["metadata"])

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": [{"id": "card-3", "question": "Q3?", "answer": "A3"}]},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        flashcards_orchestrator.run({"num_cards": 1})

    call_kwargs = mock_llm.process.call_args[1]
    existing_cards_str = call_kwargs["input_data"]["existing_cards"]
    assert "Id: card-1" in existing_cards_str
    assert "Question: What is 2+2?" in existing_cards_str
    assert "Answer: 4" in existing_cards_str
    assert "Id: card-2" in existing_cards_str
    assert "Question: Capital of France?" in existing_cards_str
    assert "Answer: Paris" in existing_cards_str


# ===========================================================================
# FlashCardsOrchestrator.run — new cards extend existing (line 123)
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.flashcards_orchestrator.LLMProcessor")
def test_run_extends_existing_cards_in_session(
    mock_llm_class,
    mock_openedx_class,
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When session already has cards, run() extends the list rather than
    replacing it.
    """
    existing = [
        {"id": "card-1", "question": "Q1?", "answer": "A1"},
    ]
    flashcards_orchestrator.session.metadata = {"cards": existing}
    flashcards_orchestrator.session.save(update_fields=["metadata"])

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"content": "course content"}
    mock_openedx_class.return_value = mock_openedx

    new_cards = [
        {"id": "card-2", "question": "Q2?", "answer": "A2"},
    ]
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": {"cards": new_cards},
    }
    mock_llm_class.return_value = mock_llm

    with patch.object(flashcards_orchestrator, "_emit_workflow_event"):
        flashcards_orchestrator.run({"num_cards": 1})

    flashcards_orchestrator.session.refresh_from_db()
    stored = flashcards_orchestrator.session.metadata["cards"]
    assert len(stored) == 2
    assert stored[0]["id"] == "card-1"
    assert stored[1]["id"] == "card-2"


# ===========================================================================
# FlashCardsOrchestrator.save — card_stack dict unwrapping (line 145)
# ===========================================================================


@pytest.mark.django_db
def test_save_unwraps_card_stack_dict(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    When 'card_stack' is a dict containing a 'cards' key, save() extracts
    the inner list instead of storing the wrapper dict.
    """
    flashcards_orchestrator.session.metadata = {}

    inner_cards = [
        {"id": "card-1", "question": "Q1?", "answer": "A1"},
        {"id": "card-2", "question": "Q2?", "answer": "A2"},
    ]
    card_stack = {"cards": inner_cards, "created_at": 12345, "last_studied_at": 67890}
    result = flashcards_orchestrator.save({"card_stack": card_stack})

    assert result["status"] == "saved"
    assert result["message"] == "2 cards saved successfully."

    flashcards_orchestrator.session.refresh_from_db()
    assert flashcards_orchestrator.session.metadata["cards"] == inner_cards


# ===========================================================================
# ScopedSessionOrchestrator — session scoping & run_async
# ===========================================================================


@pytest.mark.django_db
def test_scoped_session_has_no_location_id(
    flashcards_orchestrator,  # pylint: disable=redefined-outer-name
):
    """
    ScopedSessionOrchestrator creates a session without location_id so it is
    shared across all locations within the same course.
    """
    assert flashcards_orchestrator.session.location_id is None


@pytest.mark.django_db
@patch(
    "openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator"
    "._execute_orchestrator_async"
)
def test_scoped_run_async_stores_location_in_metadata(
    mock_task,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
    course_key,  # pylint: disable=redefined-outer-name
):
    """
    ScopedSessionOrchestrator.run_async persists the current location_id in
    metadata (not on the session row) so the async task can recover it
    without risking a unique-constraint collision.
    """
    location = "block-v1:edX+DemoX+Demo_Course+type@vertical+block@test_unit_1"
    context = {
        "course_id": str(course_key),
        "location_id": location,
    }
    orchestrator = FlashCardsOrchestrator(
        workflow=workflow_scope,
        user=user,
        context=context,
    )

    mock_task.delay.return_value = Mock(id="celery-task-id-123")
    result = orchestrator.run_async({"num_cards": 5})

    assert result["status"] == "processing"
    assert result["task_id"] == "celery-task-id-123"

    # location_id must NOT be written to the session row
    orchestrator.session.refresh_from_db()
    assert orchestrator.session.location_id is None

    # location_id must be stored in metadata for the async task
    assert orchestrator.session.metadata["location_id"] == location
    assert orchestrator.session.metadata["task_status"] == "processing"
