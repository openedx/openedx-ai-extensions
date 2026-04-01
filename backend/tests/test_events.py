"""
Tests for openedx_ai_extensions.events (data classes and signal definition).
"""
import pytest

from openedx_ai_extensions.events.data import AIOrchestrationRequestData
from openedx_ai_extensions.events.signals import AI_ORCHESTRATION_REQUESTED

EVENT_TYPE = "org.openedx.ai_extensions.orchestration.requested.v1"


# ---------------------------------------------------------------------------
# AIOrchestrationRequestData
# ---------------------------------------------------------------------------

class TestAIOrchestrationRequestData:
    """Unit tests for the event payload data class."""

    def test_required_field_user_id(self):
        data = AIOrchestrationRequestData(user_id=42)
        assert data.user_id == 42

    def test_optional_fields_default_to_none(self):
        data = AIOrchestrationRequestData(user_id=1)
        assert data.course_id is None
        assert data.location_id is None
        assert data.ui_slot_selector_id is None

    def test_action_defaults_to_run(self):
        data = AIOrchestrationRequestData(user_id=1)
        assert data.action == "run"

    def test_user_input_defaults_to_empty_dict(self):
        data = AIOrchestrationRequestData(user_id=1)
        assert data.user_input == {}

    def test_all_fields_can_be_set(self):
        data = AIOrchestrationRequestData(
            user_id=7,
            course_id="course-v1:edX+Demo+2025",
            location_id="block-v1:edX+Demo+2025+type@html+block@abc",
            ui_slot_selector_id="SLOT_X",
            user_input={"text": "hi"},
            action="summarise",
        )
        assert data.course_id == "course-v1:edX+Demo+2025"
        assert data.ui_slot_selector_id == "SLOT_X"
        assert data.action == "summarise"

    def test_frozen_raises_on_mutation(self):
        """Data class must be immutable (frozen=True)."""
        data = AIOrchestrationRequestData(user_id=1)
        with pytest.raises(Exception):  # attr raises FrozenInstanceError
            data.user_id = 99  # type: ignore[misc]

    def test_user_input_instances_are_independent(self):
        """Each instance should get its own default dict, not a shared one."""
        a = AIOrchestrationRequestData(user_id=1)
        b = AIOrchestrationRequestData(user_id=2)
        assert a.user_input is not b.user_input


# ---------------------------------------------------------------------------
# AI_ORCHESTRATION_REQUESTED signal
# ---------------------------------------------------------------------------

class TestAIOrchestrationRequestedSignal:
    """Unit tests for the public OpenEdxPublicSignal definition."""

    def test_event_type(self):
        assert AI_ORCHESTRATION_REQUESTED.event_type == EVENT_TYPE

    def test_init_data_contains_request_key(self):
        assert "ai_orchestration_request" in AI_ORCHESTRATION_REQUESTED.init_data

    def test_init_data_maps_to_correct_class(self):
        assert (
            AI_ORCHESTRATION_REQUESTED.init_data["ai_orchestration_request"]
            is AIOrchestrationRequestData
        )
