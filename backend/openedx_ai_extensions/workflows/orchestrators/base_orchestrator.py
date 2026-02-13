"""
Base orchestrator class for AI workflow execution.
"""
import importlib
import logging

from eventtracking import tracker

logger = logging.getLogger(__name__)


class BaseOrchestrator:
    """Base class for workflow orchestrators."""

    def __init__(self, workflow, user, context):
        self.workflow = workflow
        self.user = user
        self.profile = workflow.profile
        self.location_id = context.get("location_id", None)
        self.course_id = context.get("course_id", None)

    def _emit_workflow_event(self, event_name: str) -> None:
        """
        Emit an xAPI event for this workflow.

        Args:
            event_name: The event name constant (e.g., EVENT_NAME_WORKFLOW_COMPLETED)
        """

        tracker.emit(event_name, {
            "workflow_id": str(self.workflow.id),
            "action": self.workflow.action,
            "course_id": str(self.course_id),
            "profile_name": self.profile.slug,
            "location_id": str(self.location_id),
        })

    def run(self, input_data):
        raise NotImplementedError("Subclasses must implement run method")

    @classmethod
    def get_orchestrator(cls, *, workflow, user, context):
        """
        Resolve and instantiate an orchestrator for the given workflow.

        This factory method centralizes orchestrator lookup and validation.
        It ensures that the resolved class exists and is a subclass of
        BaseOrchestrator, providing a single, consistent entry point
        for orchestrator creation across the codebase.

        Args:
            workflow: AIWorkflowScope instance that defines the workflow configuration.
            user: User for whom the workflow is being executed.
            context: Dictionary with runtime context (e.g. course_id, location_id).

        Returns:
            BaseOrchestrator: An instantiated orchestrator for the given workflow.

        Raises:
            AttributeError: If the configured orchestrator class cannot be found.
            TypeError: If the resolved class is not a subclass of BaseOrchestrator.
        """
        orchestrator_name = workflow.profile.orchestrator_class

        LOCAL_PATH_MAPPING = {
            "MockResponse": "openedx_ai_extensions.workflows.orchestrators.mock_orchestrator",
            "MockStreamResponse": "openedx_ai_extensions.workflows.orchestrators.mock_orchestrator",
            "DirectLLMResponse": "openedx_ai_extensions.workflows.orchestrators.direct_orchestrator",
            "EducatorAssistantOrchestrator": "openedx_ai_extensions.workflows.orchestrators.direct_orchestrator",
            "ThreadedLLMResponse": "openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator",
        }

        try:
            if orchestrator_name in LOCAL_PATH_MAPPING:
                module_path = LOCAL_PATH_MAPPING[orchestrator_name]
                class_name = orchestrator_name
            else:
                module_path, class_name = orchestrator_name.rsplit('.', 1)

            module = importlib.import_module(module_path)
            orchestrator_class = getattr(module, class_name)

        except ValueError as exc:
            raise AttributeError(f"Invalid orchestrator name format: {orchestrator_name}") from exc
        except ImportError as exc:
            raise ImportError(
                f"Could not import module '{module_path}' for orchestrator '{orchestrator_name}'"
            ) from exc
        except AttributeError as exc:
            raise AttributeError(
                f"Orchestrator class '{class_name}' not found in module '{module_path}'"
            ) from exc

        if not issubclass(orchestrator_class, BaseOrchestrator):
            raise TypeError(
                f"{class_name} is not a subclass of BaseOrchestrator"
            )

        return orchestrator_class(
            workflow=workflow,
            user=user,
            context=context,
        )
