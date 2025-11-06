# ai_workflow/transformers.py

from tincan import Activity, ActivityDefinition, LanguageMap, Verb

from event_routing_backends.processors.xapi.registry import XApiTransformersRegistry  # pylint: disable=import-error
from event_routing_backends.processors.xapi.transformer import XApiTransformer  # pylint: disable=import-error
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
        workflow_id = self.get_data("data.workflow_id", required=True)
        action = self.get_data("data.action", default="unknown_action")

        return Activity(
            id=self.get_object_iri("ai_workflow", workflow_id),
            definition=ActivityDefinition(
                name=LanguageMap({constants.EN: f"AI Workflow: {action}"}),
                type=constants.XAPI_ACTIVITY_AI_WORKFLOW,
                description=LanguageMap({constants.EN: "AI-powered workflow completed by learner"}),
            ),
        )

    def get_context_activities(self):
        """
        Optionally include course context.
        """
        context_activities = super().get_context_activities()

        course_id = self.get_data("data.course_id", default=None)
        if course_id:
            context_activities.grouping = [
                Activity(
                    id=self.get_object_iri("course", course_id),
                    definition=ActivityDefinition(
                        type="http://adlnet.gov/expapi/activities/course",
                        name=LanguageMap({constants.EN: course_id}),
                    ),
                )
            ]
        return context_activities
