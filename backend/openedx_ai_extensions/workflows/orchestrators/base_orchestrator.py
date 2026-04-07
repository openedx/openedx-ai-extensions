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
        self.llm_processor = None

    def _convert_usage_to_json_serializable(self, usage) -> dict:
        """
        Convert usage data to a JSON-serializable format.

        This is necessary because usage data may contain complex objects
        (e.g. litellm Usage Pydantic models) that cannot be directly
        serialized to JSON when included in xAPI event data. This method
        first normalizes the input to a plain dict, then ensures every
        value is JSON-serializable.

        Args:
            usage: A dictionary or Pydantic model containing usage data.

        Returns:
            A new dictionary with all values converted to JSON-serializable formats.
        """
        if isinstance(usage, dict):
            usage_dict = usage
        elif hasattr(usage, "model_dump"):
            # Pydantic v2 models (e.g. litellm Usage)
            usage_dict = usage.model_dump()
        elif hasattr(usage, "dict"):
            # Pydantic v1 models
            usage_dict = usage.dict()
        else:
            usage_dict = vars(usage)

        serializable_usage = {}
        for key, value in usage_dict.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                serializable_usage[key] = value
            else:
                # For non-serializable types, convert to string representation
                serializable_usage[key] = str(value)
        return serializable_usage

    def _emit_workflow_event(self, event_name: str) -> None:
        """
        Emit an xAPI event for this workflow.

        Usage data is automatically fetched from ``self.llm_processor.get_usage()``
        when a processor has been set on the orchestrator.

        Args:
            event_name: The event name constant (e.g., EVENT_NAME_WORKFLOW_COMPLETED)
        """
        usage = None
        if self.llm_processor is not None:
            usage = self.llm_processor.get_usage()
        event_data = {
            "workflow_id": str(self.workflow.id),
            "action": self.workflow.action,
            "course_id": str(self.course_id) if self.course_id else "",
            "profile_name": self.profile.slug,
            "location_id": str(self.location_id) if self.location_id else "",
        }
        if self.user and hasattr(self.user, "id") and self.user.id:
            event_data["user_id"] = self.user.id
        if usage:
            event_data["usage"] = self._convert_usage_to_json_serializable(usage)

        tracking_context = {}
        if self.course_id:
            tracking_context["course_id"] = str(self.course_id)

        if tracking_context:
            with tracker.get_tracker().context("ai_workflow", tracking_context):
                tracker.emit(event_name, event_data)
        else:
            tracker.emit(event_name, event_data)

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
