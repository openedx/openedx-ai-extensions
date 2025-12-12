"""xAPI transformers for AI workflow events."""

from tincan import Activity, ActivityDefinition, Extensions, LanguageMap, Verb

from openedx_ai_extensions.edxapp_wrapper.event_routing_module import XApiTransformer, XApiTransformersRegistry
from openedx_ai_extensions.workflows.processors.xapi import constants


@XApiTransformersRegistry.register("openedx.ai.workflow.completed")
class AIWorkflowCompletedTransformer(XApiTransformer):
    """
    xAPI Transformer for a successfully completed AI workflow.

    Transforms the 'openedx.ai.workflow.completed' event into an xAPI statement
    following the Open edX xAPI specification pattern for assessments and activities.
    """

    _verb = Verb(
        id=constants.XAPI_VERB_COMPLETED,
        display=LanguageMap({constants.EN: constants.COMPLETED}),
    )

    def get_object(self):
        """
        Construct the xAPI object for the completed AI workflow.

        The activity object includes:
        - A unique ID for this workflow instance
        - A custom activity type (https://w3id.org/xapi/openedx/activity/ai-workflow)
        - Name derived from the config filename (e.g., "openai_threads")
        - Extensions with workflow metadata:
          - action: The workflow action
          - prompt-template-slug: Placeholder for future prompt template tracking
          - location-id: The Open edX location/unit where the workflow was triggered

        Returns:
            `Activity`: The xAPI Activity object representing the AI workflow
        """
        workflow_id = self.get_data("workflow_id", True)
        action = self.get_data("action") or "unknown-action"
        workflow_name = self.get_data("workflow_name") or action

        # Build extensions
        extensions = {
            constants.XAPI_EXTENSION_WORKFLOW_ACTION: action,
        }

        # Add prompt template slug if available (placeholder for now)
        prompt_template = self.get_data("prompt_template_slug")
        if prompt_template:
            extensions[constants.XAPI_EXTENSION_PROMPT_TEMPLATE_SLUG] = prompt_template

        # Add location_id if available
        location_id = self.get_data("location_id")
        if location_id:
            extensions[constants.XAPI_EXTENSION_LOCATION_ID] = location_id

        return Activity(
            id=self.get_object_iri("ai_workflow", workflow_id),
            definition=ActivityDefinition(
                type=constants.XAPI_ACTIVITY_AI_WORKFLOW,
                name=LanguageMap({constants.EN: workflow_name}),
                description=LanguageMap({
                    constants.EN: "AI-powered educational workflow"
                }),
                extensions=Extensions(extensions),
            ),
        )
