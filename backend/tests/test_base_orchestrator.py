"""
Tests for the BaseOrchestrator class in openedx-ai-extensions workflows module.
"""

from unittest.mock import patch

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
    Test that _emit_workflow_event calls tracker.emit with correct payload.
    """
    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator(workflow=mock_workflow, user=mock_user, context=context)

    orchestrator._emit_workflow_event("TEST_EVENT")  # pylint: disable=protected-access

    mock_tracker.emit.assert_called_once_with("TEST_EVENT", {
        "workflow_id": str(mock_workflow.id),
        "action": mock_workflow.action,
        "course_id": str("course-1"),
        "profile_name": mock_workflow.profile.slug,
        "location_id": str("loc-1"),
    })


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
def test_get_orchestrator_success(monkeypatch, mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator returns an instance of the resolved class.
    """
    from openedx_ai_extensions.workflows.orchestrators import orchestrators  # pylint: disable=import-outside-toplevel

    class MockOrchestrator(BaseOrchestrator):
        def run(self, input_data):
            return {"status": "ok"}

    monkeypatch.setitem(orchestrators.__dict__, "MockOrchestrator", MockOrchestrator)

    context = {"location_id": "loc-1", "course_id": "course-1"}
    orchestrator = BaseOrchestrator.get_orchestrator(
        workflow=mock_workflow,
        user=mock_user,
        context=context
    )

    assert isinstance(orchestrator, MockOrchestrator)
    assert orchestrator.workflow == mock_workflow
    assert orchestrator.user == mock_user


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
def test_get_orchestrator_type_error(monkeypatch, mock_workflow, mock_user):  # pylint: disable=redefined-outer-name
    """
    Test get_orchestrator raises TypeError when resolved class is not a subclass of BaseOrchestrator.
    """
    from openedx_ai_extensions.workflows.orchestrators import orchestrators  # pylint: disable=import-outside-toplevel

    class NotAnOrchestrator:
        pass

    monkeypatch.setitem(orchestrators.__dict__, "MockOrchestrator", NotAnOrchestrator)

    context = {"location_id": None, "course_id": None}

    with pytest.raises(TypeError) as exc_info:
        BaseOrchestrator.get_orchestrator(workflow=mock_workflow, user=mock_user, context=context)

    assert "MockOrchestrator is not a subclass of BaseOrchestrator" in str(exc_info.value)


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
@patch("openedx_ai_extensions.workflows.orchestrators.importlib.import_module")
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

    # The outer exception handler catches and re-raises, so we see its message
    assert "Orchestrator class 'some.module.NonExistentOrchestrator' not found" in str(exc_info.value)
