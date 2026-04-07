"""
Django signal receivers for openedx-ai-extensions.

This is the entry point that bridges the event bus → orchestrator.
"""
import logging

from django.contrib.auth import get_user_model
from django.dispatch import receiver

from openedx_ai_extensions.events.signals import AI_ORCHESTRATION_REQUESTED
from openedx_ai_extensions.workflows.models import AIWorkflowScope

log = logging.getLogger(__name__)


@receiver(AI_ORCHESTRATION_REQUESTED)
def handle_ai_orchestration_requested(_sender, ai_orchestration_request, **kwargs):
    """
    Triggered when any app publishes AI_ORCHESTRATION_REQUESTED.

    Either in-process (direct Django signal) or via the event bus consumer loop.
    Looks up the AIWorkflowProfile by slug and runs the orchestrator.
    """
    User = get_user_model()

    # Run the orchestrator with the provided input data
    try:
        user = User.objects.get(id=ai_orchestration_request.user_id)

        def compact(d: dict) -> dict:
            return {k: v for k, v in d.items() if v is not None}

        context = compact({
            "course_id": ai_orchestration_request.course_id,
            "location_id": ai_orchestration_request.location_id,
            "ui_slot_selector_id": ai_orchestration_request.ui_slot_selector_id,
        })

        workflow = AIWorkflowScope.get_profile(**context)
        if workflow is None:
            log.error(
                "No workflow profile found for orchestration request. Context: %s",
                context,
            )
            return
        workflow.execute(
            user_input=ai_orchestration_request.user_input,
            action=ai_orchestration_request.action,
            user=user,
            running_context=context,
        )
    except Exception:
        log.exception("Error running orchestrator for workflow")
        raise
