"""
Attr data classes for AI Extensions events.
These are owned by openedx-ai-extensions and imported by any app that
wants to request an AI orchestration run.
"""
import attr


@attr.s(frozen=True)
class AIOrchestrationRequestData:
    """
    Payload for requesting an AI workflow run via the event bus.
    """
    user_id = attr.ib(type=int)
    course_id = attr.ib(type=str, default=None)
    location_id = attr.ib(type=str, default=None)
    ui_slot_selector_id = attr.ib(type=str, default=None)
    user_input = attr.ib(type=dict, factory=dict)
    action = attr.ib(type=str, default="run")
