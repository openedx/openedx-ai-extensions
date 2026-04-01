"""
Django signal receivers for openedx-ai-extensions.
This is the entry point that bridges the event bus → orchestrator.
"""
import logging
import profile

from django.dispatch import receiver

from openedx_ai_extensions.events.signals import AI_ORCHESTRATION_REQUESTED

log = logging.getLogger(__name__)


@receiver(AI_ORCHESTRATION_REQUESTED)
def handle_ai_orchestration_requested(sender, ai_orchestration_request, **kwargs):
    """
    Triggered when any app publishes AI_ORCHESTRATION_REQUESTED, either
    in-process (direct Django signal) or via the event bus consumer loop.

    Looks up the AIWorkflowProfile by slug and runs the orchestrator.
    """
    from openedx_ai_extensions.workflows.models import AIWorkflowScope
    from django.contrib.auth import get_user_model

    User = get_user_model()

    # Run the orchestrator with the provided input data
    try:
        user = User.objects.get(id=ai_orchestration_request.user_id) if ai_orchestration_request.user_id else None
        context = {
            k: v
            for k, v in {
                "course_id": ai_orchestration_request.course_id if ai_orchestration_request.course_id else None,
                "location_id": ai_orchestration_request.location_id if ai_orchestration_request.location_id else None,
                "ui_slot_selector_id": ai_orchestration_request.ui_slot_selector_id,
            }.items()
            if v is not None
        }

        workflow = AIWorkflowScope.get_profile(**context)
        log.info("Found workflow profile for orchestration request. Context: %s", context)
        result = workflow.execute(
            user_input=ai_orchestration_request.user_input,
            action=ai_orchestration_request.action,
            user=user,
            running_context=context,
        )
        log.info("Successfully ran orchestrator for workflow. Context: %s", context)
    except Exception:
        log.exception("Error running orchestrator for workflow")
