"""xAPI transformers for AI workflow events."""

from tincan import Activity, ActivityDefinition, LanguageMap, Verb

from openedx_ai_extensions.edxapp_wrapper.event_routing_module import XApiTransformer, XApiTransformersRegistry
from openedx_ai_extensions.workflows.processors.xapi import constants


@XApiTransformersRegistry.register("openedx.ai.workflow.completed")
class AIWorkflowCompletedTransformer(XApiTransformer):
    """
    xAPI Transformer for a successfully completed AI workflow.
    """

    _verb = Verb(
        id=constants.XAPI_VERB_COMPLETED,
        display=LanguageMap({constants.EN: constants.COMPLETED}),
    )

    def get_object(self):
        """
        Construct the xAPI object for the completed AI workflow.
        Returns:
            `Activity`
        """
        workflow_id = self.get_data("workflow_id", True)
        action = self.get_data("action") or "unknown_action"

        return Activity(
            id=self.get_object_iri("ai_workflow", workflow_id),
            definition=ActivityDefinition(
                name=LanguageMap({constants.EN: f"AI Workflow: {action}"}),
                type=constants.XAPI_ACTIVITY_AI_WORKFLOW,
                description=LanguageMap({constants.EN: "AI-powered workflow completed by learner"}),
            ),
        )
