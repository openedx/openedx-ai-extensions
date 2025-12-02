"""
AI Workflow models for managing flexible AI workflow execution
"""

import logging
from typing import Any, Optional
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

from openedx_ai_extensions.workflows.configs.mock_functions import _fake_get_config_from_file

User = get_user_model()
logger = logging.getLogger(__name__)


class AIWorkflowConfig(models.Model):
    """
    Configuration templates for different AI workflows

    .. no_pii:
    """

    action = models.CharField(
        max_length=100,
        help_text="Action identifier (e.g., 'summarize', 'quiz_generate')",
    )
    course_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Course this config applies to (null = global)",
    )

    location_id = UsageKeyField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Location this config applies to",
    )

    # Orchestrator configuration
    orchestrator_class = models.CharField(
        max_length=255, help_text="Full class name of the orchestrator"
    )

    # Processor configuration (LLM settings, templates, etc.)
    processor_config = models.JSONField(
        default=dict, help_text="LLM provider, model, template settings"
    )

    # Actuator configuration (response format, UI components, etc.)
    actuator_config = models.JSONField(
        default=dict, help_text="Response formatting and UI settings"
    )

    # Requirements
    # TODO: how do we enforce context requirements

    # Metadata
    # TODO: add an enabled field

    class Meta:
        unique_together = ["action", "course_id"]
        indexes = [
            models.Index(fields=["action", "course_id"]),
        ]

    def __str__(self):
        course_part = f" (Course: {self.course_id})" if self.course_id else " (Global)"
        return f"{self.action}{course_part}"

    @classmethod
    def get_config(
        cls, action: str, course_id: Optional[str] = None, location_id: Optional[str] = None
    ):
        """
        Get configuration for a specific action, course, and location.

        In real implementation, this would query the database.
        Currently uses a fake method to simulate loading config from file.
        """
        # In real implementation, this would query the database
        return _fake_get_config_from_file(
            cls, action=action, course_id=course_id, location_id=location_id
        )


class AIWorkflow(models.Model):
    """
    Individual AI workflow instances with state management

    .. pii: This model contains a user reference
    .. pii_types: id
    .. pii_retirement: retained
    """

    # Core identification fields
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text="User who initiated this workflow"
    )
    action = models.CharField(max_length=100, help_text="Action identifier")

    # Context fields (nullable for flexibility)
    course_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="Course context"
    )
    location_id = UsageKeyField(
        max_length=255, null=True, blank=True, help_text="Location context"
    )

    # Workflow execution state
    config = models.ForeignKey(
        AIWorkflowConfig,
        on_delete=models.CASCADE,
        help_text="Configuration used for this workflow",
    )

    # TODO: think about partial execution with multiple trips for user info
    # current_step = models.CharField(max_length=100, default="start", help_text="Current step in workflow execution")
    status = models.CharField(
        max_length=50,
        default="active",
        choices=[
            ("active", "Active"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("paused", "Paused"),
        ],
    )

    # Data storage
    context_data = models.JSONField(
        default=dict, help_text="Workflow context and intermediate data"
    )
    extra_context = models.JSONField(
        default=dict, help_text="Additional context from request"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Unique constraint on the natural key
        unique_together = ["user", "action", "course_id", "location_id"]
        indexes = [
            models.Index(fields=["user", "action", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.status}"

    def get_natural_key(self) -> str:
        """Get natural identification key for this workflow"""
        parts = [str(self.user.id), self.action]
        if self.course_id:
            parts.append(str(self.course_id))
        if self.location_id:
            parts.append(str(self.location_id))
        return "__".join(parts)

    @staticmethod
    def get_context_from_request(request_body: dict, user) -> dict:
        """
        Standardized context for workflow lookup.
        Always returns dict with keys: action, course_id, location_id, user
        """
        return {
            "action": request_body.get("action"),
            "course_id": request_body.get("courseId"),
            "location_id": request_body.get("context", {}).get("locationId"),
            "user": user,
        }

    @classmethod
    def find_workflow_for_context(
        cls,
        *,
        action: str,
        course_id: Optional[str] = None,
        user,
        location_id: Optional[str] = None,
    ) -> tuple["AIWorkflow", bool]:
        """
        Find or create workflow based on action, course, user and context
        This is the main entry point for the API

        Returns: (workflow_instance, created_boolean)
        """

        # Get workflow configuration
        config = AIWorkflowConfig.get_config(action, course_id, location_id)
        if not config:
            raise ValidationError(
                f"No AIWorkflowConfiguration found for action '{action}' in course '{course_id}'"
            )

        # Get or create workflow using natural key
        # workflow, created = cls.objects.get_or_create(
        workflow = cls(
            user=user,
            action=action,
            course_id=course_id,
            location_id=location_id,
            config=config,
            context_data={},
        )
        created = True

        return workflow, created

    def execute(self, user_input) -> dict[str, str | dict[str, str]] | Any:
        """
        Execute this workflow using its configured orchestrator
        This is where the actual AI processing happens

        Returns: Dictionary with execution results
        """

        try:
            # Load the orchestrator for this workflow
            from openedx_ai_extensions.workflows import orchestrators  # pylint: disable=import-outside-toplevel

            orchestrator_name = self.config.orchestrator_class  # "DirectLLMResponse"
            orchestrator = getattr(orchestrators, orchestrator_name)(workflow=self)

            if not hasattr(orchestrator, self.action):
                raise NotImplementedError(
                    f"Orchestrator '{orchestrator_name}' does not implement action '{self.action}'"
                )
            result = getattr(orchestrator, self.action)(user_input)

            # Emit event - will be filtered by whitelist processor and routed to xapi backend
            config_filename = self.config.processor_config.get("_config_filename", self.action)
            # Build a clean workflow ID using config filename and action
            workflow_id = f"{config_filename}__{self.action}"

            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                f"🤖 WORKFLOW EXECUTOR ERROR: {str(e)} for {self.get_natural_key()}"
            )

            # Mark workflow as failed
            self.status = "failed"
            self.current_step = "failed"  # pylint: disable=attribute-defined-outside-init
            self.context_data["error"] = str(e)
            self.context_data["failed_at"] = timezone.now().isoformat()
            # self.save(update_fields=['status', 'current_step', 'context_data', 'updated_at'])

            # Return error result
            return {
                "error": f"Workflow execution failed: {str(e)}",
                "status": "error",
                "workflow_info": {
                    "natural_key": self.get_natural_key(),
                    "status": self.status,
                    "current_step": self.current_step,
                },
            }

    def _load_orchestrator(self):
        """Load the orchestrator for this workflow"""
        # This method is currently unused - orchestrator loading happens in execute()
        # TODO: Refactor to use this method or remove it
        from openedx_ai_extensions.workflows import orchestrators  # pylint: disable=import-outside-toplevel

        orchestrator_name = self.config.orchestrator_class
        return getattr(orchestrators, orchestrator_name)(workflow=self)

    def update_context(self, **kwargs):
        """Update context data"""
        self.context_data.update(kwargs)
        # self.save(update_fields=['context_data', 'updated_at'])

    def set_step(self, step: str, status: Optional[str] = None):
        """Update current step and optionally status"""
        self.current_step = step  # pylint: disable=attribute-defined-outside-init
        if status:
            self.status = status
        # self.save(update_fields=['current_step', 'status', 'updated_at'])

    def complete(self, **final_context):
        """Mark workflow as completed with final context"""
        self.status = "completed"
        self.current_step = "completed"  # pylint: disable=attribute-defined-outside-init
        self.completed_at = timezone.now()
        if final_context:
            self.context_data.update(final_context)
        # self.save(update_fields=['status', 'current_step', 'completed_at', 'context_data', 'updated_at'])


class AIWorkflowSession(models.Model):
    """
    Sessions for tracking user interactions within AI workflows

    .. pii: This model contains a user reference
    .. pii_types: id
    .. pii_retirement: retained
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text="User associated with this session"
    )
    course_id = CourseKeyField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Course associated with this session"
    )
    location_id = UsageKeyField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Location associated with this session",
    )
    local_submission_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID of the submission associated with this session",
    )

    remote_response_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID of the last response sent to the user",
    )
    metadata = models.JSONField(default=dict, help_text="Additional session metadata")
