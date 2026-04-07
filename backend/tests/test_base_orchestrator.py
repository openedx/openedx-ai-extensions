"""
Tests for the BaseOrchestrator class in openedx-ai-extensions workflows module.
"""
# pylint: disable=import-outside-toplevel

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from openedx_ai_extensions.workflows.orchestrators import BaseOrchestrator

User = get_user_model()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_user(db):  # pylint: disable=unused-argument
    """
    Create a test user.
    """
    return User.objects.create_user(
        username="testuser2", email="test2@example.com", password="password123"
    )


@pytest.fixture
def mock_workflow_profile():
    """
    Create a fake workflow profile object with orchestrator_class attribute.
    """
    class Profile:
        slug = "mock-profile"
        orchestrator_class = "MockOrchestrator"

    return Profile()


@pytest.fixture
def mock_workflow(mock_workflow_profile):  # pylint: disable=redefined-outer-name
    """
    Create a fake workflow object with profile and action attributes.
    """
    class Workflow:
        id = 123
        profile = mock_workflow_profile
        action = "test_action"

    return Workflow()


# ============================================================================
# BaseOrchestrator Initialization Tests
# ============================================================================

@pytest.mark.django_db
def test_base_orchestrator_init(mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test that BaseOrchestrator initializes attributes correctly.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    assert orchestrator.workflow == mock_workflow
    assert orchestrator.user == mock_user
    assert orchestrator.profile == mock_workflow.profile
    assert orchestrator.location_id == "loc-1"
    assert orchestrator.course_id == "course-1"


# ============================================================================
# _emit_workflow_event Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event(mock_tracker, mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event calls tracker.emit with correct payload
    and sets the tracking context with course_id.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    # Verify tracking context was entered with course_id
    mock_tracker.get_tracker.return_value.context.assert_called_once_with(
        "ai_workflow", {"course_id": "course-1"}
    )

    # Verify emit was called with correct payload
    mock_tracker.emit.assert_called_once_with("TEST_EVENT", {
        "workflow_id": str(mock_workflow.id),
        "action": mock_workflow.action,
        "course_id": "course-1",
        "profile_name": mock_workflow.profile.slug,
        "location_id": "loc-1",
        "user_id": mock_user.id,
    })


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_with_usage(
    mock_tracker,
    mock_workflow,
    mock_user
  ):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event includes serialized usage data when provided.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    mock_processor = MagicMock()
    mock_processor.get_usage.return_value = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    orchestrator.llm_processor = mock_processor
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    mock_tracker.emit.assert_called_once_with("TEST_EVENT", {
        "workflow_id": str(mock_workflow.id),
        "action": mock_workflow.action,
        "course_id": "course-1",
        "profile_name": mock_workflow.profile.slug,
        "location_id": "loc-1",
        "user_id": mock_user.id,
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    })


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_with_pydantic_usage(
    mock_tracker,
    mock_workflow,
    mock_user
  ):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event correctly serializes a Pydantic v2 usage object (e.g. litellm Usage).
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    mock_usage = MagicMock()
    del mock_usage.dict  # force pydantic v2 path
    mock_usage.model_dump.return_value = {
        "prompt_tokens": 5,
        "completion_tokens": 15,
        "total_tokens": 20,
    }

    mock_processor = MagicMock()
    mock_processor.get_usage.return_value = mock_usage
    orchestrator.llm_processor = mock_processor
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    call_args = mock_tracker.emit.call_args
    assert call_args[0][1]["usage"] == {
        "prompt_tokens": 5,
        "completion_tokens": 15,
        "total_tokens": 20,
    }


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_without_location_id(
    mock_tracker,
    mock_workflow,
    mock_user
  ):  # pylint: disable=redefined-outer-name
    """
    Test that when location_id is absent, it defaults to an empty string in the payload.
    """
    context = {"course_id": "course-1"}  # no location_id
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    mock_tracker.emit.assert_called_once_with("TEST_EVENT", {
        "workflow_id": str(mock_workflow.id),
        "action": mock_workflow.action,
        "course_id": "course-1",
        "profile_name": mock_workflow.profile.slug,
        "location_id": "",
        "user_id": mock_user.id,
    })


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_usage_none_excluded(
    mock_tracker, mock_workflow, mock_user
):  # pylint: disable=redefined-outer-name
    """
    Test that when usage is None (default), the 'usage' key is NOT present in the emitted payload.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    call_args = mock_tracker.emit.call_args
    assert "usage" not in call_args[0][1]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_no_course_id(
    mock_tracker, mock_workflow, mock_user
):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event works without a course_id —
    no tracking context is entered, emit is still called.
    """
    context = {"location_id": "loc-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    # Verify no tracking context was entered (no course_id)
    mock_tracker.get_tracker.return_value.context.assert_not_called()

    # Verify emit was still called
    mock_tracker.emit.assert_called_once_with("TEST_EVENT", {
        "workflow_id": str(mock_workflow.id),
        "action": mock_workflow.action,
        "course_id": "",
        "profile_name": mock_workflow.profile.slug,
        "location_id": "loc-1",
        "user_id": mock_user.id,
    })


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_with_pydantic_v1_usage(
    mock_tracker,
    mock_workflow,
    mock_user
  ):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event correctly serializes a Pydantic v1 usage object.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    mock_usage = MagicMock()
    # Mock Pydantic v1 behavior: has .dict() but NOT .model_dump()
    del mock_usage.model_dump
    mock_usage.dict.return_value = {
        "prompt_tokens": 5,
        "completion_tokens": 15,
        "total_tokens": 20,
    }

    mock_processor = MagicMock()
    mock_processor.get_usage.return_value = mock_usage
    orchestrator.llm_processor = mock_processor
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    call_args = mock_tracker.emit.call_args
    assert call_args[0][1]["usage"] == {
        "prompt_tokens": 5,
        "completion_tokens": 15,
        "total_tokens": 20,
    }


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_with_custom_object_usage(
    mock_tracker,
    mock_workflow,
    mock_user
  ):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event correctly serializes a custom object using vars().
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    class CustomUsage:
        def __init__(self):
            self.prompt_tokens = 5
            self.completion_tokens = 15
            self.total_tokens = 20

    mock_processor = MagicMock()
    mock_processor.get_usage.return_value = CustomUsage()
    orchestrator.llm_processor = mock_processor
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    call_args = mock_tracker.emit.call_args
    assert call_args[0][1]["usage"] == {
        "prompt_tokens": 5,
        "completion_tokens": 15,
        "total_tokens": 20,
    }


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.tracker")
def test_emit_workflow_event_with_non_serializable_usage_value(
    mock_tracker,
    mock_workflow,
    mock_user
  ):  # pylint: disable=redefined-outer-name
    """
    Test that _emit_workflow_event converts non-serializable values to strings.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    class NonSerializable:
        def __str__(self):
            return "Non-Serializable Object"

    mock_processor = MagicMock()
    mock_processor.get_usage.return_value = {"custom_field": NonSerializable()}
    orchestrator.llm_processor = mock_processor
    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    call_args = mock_tracker.emit.call_args
    assert call_args[0][1]["usage"] == {"custom_field": "Non-Serializable Object"}


# ============================================================================
# run Method Tests
# ============================================================================

@pytest.mark.django_db
def test_base_orchestrator_run_raises_not_implemented(mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test that calling run on BaseOrchestrator raises NotImplementedError.
    """
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context={})
    with pytest.raises(NotImplementedError):
        orchestrator.run({})


# ============================================================================
# get_orchestrator Classmethod Tests
# ============================================================================

@pytest.mark.django_db
def test_get_orchestrator_attribute_error(mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator raises AttributeError when class does not exist.
    """
    mock_workflow.profile.orchestrator_class = "NonExistingClass"
    context = {"location_id": None, "course_id": None}

    with pytest.raises(AttributeError) as exc_info:
        BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    assert "NonExistingClass" in str(exc_info.value)


@pytest.mark.django_db
def test_get_orchestrator_import_error(mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator raises ImportError when module path is invalid.
    """
    # Use a dotted path with a non-existent module
    mock_workflow.profile.orchestrator_class = "non_existent_module.path.SomeOrchestrator"
    context = {"location_id": None, "course_id": None}

    with pytest.raises(ImportError) as exc_info:
        BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    assert "Could not import module" in str(exc_info.value)
    assert "non_existent_module.path" in str(exc_info.value)


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.importlib.import_module")
def test_get_orchestrator_class_not_found_in_module(
    mock_import, mock_workflow, mock_user
):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator raises AttributeError when class doesn't exist in a valid module.
    This tests the inner AttributeError handling when getattr fails (lines 196-199),
    though the error is re-raised and caught by the outer handler.
    """
    # Mock a module that imports successfully but doesn't have the required class
    mock_module = type('MockModule', (), {})()
    mock_import.return_value = mock_module

    # Use a dotted path with a valid module but non-existent class
    mock_workflow.profile.orchestrator_class = "some.module.NonExistentOrchestrator"
    context = {"location_id": None, "course_id": None}

    with pytest.raises(AttributeError) as exc_info:
        BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    # The error message should contain the class name and module path
    assert "Orchestrator class 'NonExistentOrchestrator' not found in module 'some.module'" in str(exc_info.value)


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.base_orchestrator.importlib.import_module")
def test_get_orchestrator_not_subclass_error(
    mock_import, mock_workflow, mock_user
):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator raises TypeError when class is not a subclass of BaseOrchestrator.
    """
    class NotAnOrchestrator:
        pass

    mock_module = MagicMock()
    mock_module.SomeClass = NotAnOrchestrator
    mock_import.return_value = mock_module

    mock_workflow.profile.orchestrator_class = "some.module.SomeClass"
    context = {"location_id": None, "course_id": None}

    with pytest.raises(TypeError) as exc_info:
        BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    assert "is not a subclass of BaseOrchestrator" in str(exc_info.value)


@pytest.mark.django_db
def test_get_orchestrator_invalid_format_error(mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator raises AttributeError when format is invalid (no dots).
    """
    mock_workflow.profile.orchestrator_class = "InvalidFormat"  # No dots, not in mapping
    context = {"location_id": None, "course_id": None}

    with pytest.raises(AttributeError) as exc_info:
        BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    assert "Invalid orchestrator name format" in str(exc_info.value)


@pytest.mark.django_db
def test_get_orchestrator_success(mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator successfully returns an orchestrator instance.
    """
    mock_workflow.profile.orchestrator_class = "DirectLLMResponse"
    context = {"location_id": "loc-1", "course_id": "course-1"}

    orchestrator = BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    from openedx_ai_extensions.workflows.orchestrators.direct_orchestrator import DirectLLMResponse  # noqa: E501
    assert isinstance(orchestrator, DirectLLMResponse)
    assert orchestrator.user == mock_user
    assert orchestrator.location_id == "loc-1"
