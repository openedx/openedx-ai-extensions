"""xAPI transformers for AI workflow events."""

from event_routing_backends.processors.xapi.registry import XApiTransformersRegistry
from event_routing_backends.processors.xapi.transformer import XApiTransformer
from tincan import Activity, ActivityDefinition, Extensions, LanguageMap, Verb

from openedx_ai_extensions.xapi import constants


class BaseAIWorkflowTransformer(XApiTransformer):
    """
    Base transformer for all AI workflow events.

    Provides common object construction for AI workflow activities.
    Subclasses only need to define the appropriate verb.
    """

    def get_object(self):
        """
        Construct the xAPI object for AI workflow events.

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


@XApiTransformersRegistry.register("openedx.ai.workflow.initialized")
class AIWorkflowInitializedTransformer(BaseAIWorkflowTransformer):
    """
    xAPI Transformer for initializing a threaded AI workflow.

    Emitted when a conversational/threaded workflow is started for the first time.
    """

    _verb = Verb(
        id=constants.XAPI_VERB_INITIALIZED,
        display=LanguageMap({constants.EN: constants.INITIALIZED}),
    )


@XApiTransformersRegistry.register("openedx.ai.workflow.interacted")
class AIWorkflowInteractedTransformer(BaseAIWorkflowTransformer):
    """
    xAPI Transformer for interactions within a threaded AI workflow.

    Emitted for each subsequent interaction in a conversational workflow
    (after initialization).
    """

    _verb = Verb(
        id=constants.XAPI_VERB_INTERACTED,
        display=LanguageMap({constants.EN: constants.INTERACTED}),
    )


@XApiTransformersRegistry.register("openedx.ai.workflow.completed")
class AIWorkflowCompletedTransformer(BaseAIWorkflowTransformer):
    """
    xAPI Transformer for a one-shot AI workflow completion.

    Emitted when a non-threaded workflow completes (e.g., summarize, explain_like_five).
    These workflows don't have back-and-forth interactions - they're single request/response.
    """

    _verb = Verb(
        id=constants.XAPI_VERB_COMPLETED,
        display=LanguageMap({constants.EN: constants.COMPLETED}),
    )
