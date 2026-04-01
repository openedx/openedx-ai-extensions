"""
Public OpenEdxPublicSignal owned by openedx-ai-extensions.

External apps import this signal to request an AI workflow run.
openedx-ai-extensions is the sole consumer.
"""
from openedx_events.tooling import OpenEdxPublicSignal

from openedx_ai_extensions.events.data import AIOrchestrationRequestData

AI_ORCHESTRATION_REQUESTED = OpenEdxPublicSignal(
    event_type="org.openedx.ai_extensions.orchestration.requested.v1",
    data={
        "ai_orchestration_request": AIOrchestrationRequestData,
    }
)
