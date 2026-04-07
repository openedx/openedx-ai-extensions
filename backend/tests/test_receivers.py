"""
Tests for openedx_ai_extensions.receivers.

Covers the handle_ai_orchestration_requested signal receiver:
- happy path (workflow found, execute called)
- no workflow found (early return, error logged)
- exceptions are re-raised
- None-valued context fields are filtered out (compact behaviour)
- receiver is wired to AI_ORCHESTRATION_REQUESTED
"""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from openedx_ai_extensions.events.data import AIOrchestrationRequestData
from openedx_ai_extensions.events.signals import AI_ORCHESTRATION_REQUESTED
from openedx_ai_extensions.receivers import handle_ai_orchestration_requested

User = get_user_model()

EVENT_TYPE = "org.openedx.ai_extensions.orchestration.requested.v1"

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def regular_user(db):  # pylint: disable=unused-argument
    return User.objects.create_user(
        username="receiver_test_user",
        email="receiver@example.com",
        password="secret",
    )


def _make_request(**kwargs):
    """Return an AIOrchestrationRequestData with sensible defaults."""
    defaults = {
        "user_id": 1,
        "course_id": "course-v1:edX+Demo+2025",
        "location_id": None,
        "ui_slot_selector_id": "SLOT_A",
        "user_input": {"text": "hello"},
        "action": "run",
    }
    defaults.update(kwargs)
    return AIOrchestrationRequestData(**defaults)


def _call_handler(request_data):
    """Call the receiver directly, bypassing send_robust signal dispatch."""
    handle_ai_orchestration_requested(
        None,
        ai_orchestration_request=request_data,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_happy_path_executes_workflow(regular_user):  # pylint: disable=redefined-outer-name
    """Workflow is found and execute() is called with the right arguments."""
    request_data = _make_request(user_id=regular_user.id)
    mock_workflow = MagicMock()

    with patch(
        "openedx_ai_extensions.receivers.AIWorkflowScope.get_profile",
        return_value=mock_workflow,
    ):
        _call_handler(request_data)

    mock_workflow.execute.assert_called_once_with(
        user_input=request_data.user_input,
        action=request_data.action,
        user=regular_user,
        running_context={
            "course_id": request_data.course_id,
            "ui_slot_selector_id": request_data.ui_slot_selector_id,
            # location_id is None → must be absent (compact removes it)
        },
    )


@pytest.mark.django_db
def test_no_workflow_returns_early_and_logs(regular_user):  # pylint: disable=redefined-outer-name
    """When get_profile() returns None the receiver logs an error and returns."""
    request_data = _make_request(user_id=regular_user.id)

    with patch(
        "openedx_ai_extensions.receivers.AIWorkflowScope.get_profile",
        return_value=None,
    ), patch("openedx_ai_extensions.receivers.log") as mock_log:
        _call_handler(request_data)

    mock_log.error.assert_called_once()


@pytest.mark.django_db
def test_exception_is_reraised(regular_user):  # pylint: disable=redefined-outer-name
    """Exceptions from execute() are logged and then re-raised."""
    request_data = _make_request(user_id=regular_user.id)
    boom = RuntimeError("something went wrong")
    mock_workflow = MagicMock()
    mock_workflow.execute.side_effect = boom

    with patch(
        "openedx_ai_extensions.receivers.AIWorkflowScope.get_profile",
        return_value=mock_workflow,
    ), pytest.raises(RuntimeError, match="something went wrong"):
        _call_handler(request_data)


@pytest.mark.django_db
def test_compact_filters_none_values(regular_user):  # pylint: disable=redefined-outer-name
    """None-valued fields are excluded from the context passed to get_profile."""
    request_data = _make_request(
        user_id=regular_user.id,
        course_id=None,
        location_id=None,
        ui_slot_selector_id="SLOT_B",
    )
    mock_workflow = MagicMock()

    with patch(
        "openedx_ai_extensions.receivers.AIWorkflowScope.get_profile",
        return_value=mock_workflow,
    ) as mock_get_profile:
        _call_handler(request_data)

    called_context = mock_get_profile.call_args[1]
    assert "course_id" not in called_context
    assert "location_id" not in called_context
    assert called_context["ui_slot_selector_id"] == "SLOT_B"


@pytest.mark.django_db
def test_user_not_found_raises(db):  # pylint: disable=unused-argument
    """DoesNotExist from User.objects.get is re-raised (goes through except/raise)."""
    request_data = _make_request(user_id=999_999)

    with pytest.raises(User.DoesNotExist):
        _call_handler(request_data)


def test_receiver_is_connected_to_signal():
    """The handler must be registered as a receiver for AI_ORCHESTRATION_REQUESTED."""
    # Look for the handler id in the signal's receiver list
    receiver_ids = [r[0] for r in AI_ORCHESTRATION_REQUESTED.receivers]
    handler_id = id(handle_ai_orchestration_requested)
    assert any(handler_id == rid[0] for rid in receiver_ids), (
        "handle_ai_orchestration_requested is not connected to AI_ORCHESTRATION_REQUESTED"
    )
