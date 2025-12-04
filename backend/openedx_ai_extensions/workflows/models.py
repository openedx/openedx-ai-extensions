"""
AI Workflow models for managing flexible AI workflow execution
"""

import logging
import re
from typing import Any, Dict, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

User = get_user_model()
logger = logging.getLogger(__name__)


def validate_orchestrator_class(value):
    """
    Validate that the orchestrator_class is a valid BaseOrchestrator subclass.
    """
    from openedx_ai_extensions.workflows import orchestrators  # pylint: disable=import-outside-toplevel

    if not hasattr(orchestrators, value):
        raise ValidationError(
            f"Orchestrator class '{value}' not found in orchestrators module"
        )

    orchestrator_class = getattr(orchestrators, value)

    if not isinstance(orchestrator_class, type):
        raise ValidationError(
            f"'{value}' is not a class"
        )

    if not issubclass(orchestrator_class, orchestrators.BaseOrchestrator):
        raise ValidationError(
            f"'{value}' must be a subclass of BaseOrchestrator"
        )


def validate_processor_config(value):
    """
    Validate that processor_config keys are valid processor class names.
    """
    from openedx_ai_extensions import processors  # pylint: disable=import-outside-toplevel

    if not isinstance(value, dict):
        raise ValidationError("processor_config must be a dictionary")

    for processor_name in value.keys():
        if not hasattr(processors, processor_name):
            available_processors = ", ".join(processors.__all__)
            raise ValidationError(
                f"Processor class '{processor_name}' not found in processors module. "
                f"Available processors: {available_processors}"
            )

        processor_class = getattr(processors, processor_name)

        if not isinstance(processor_class, type):
            raise ValidationError(
                f"'{processor_name}' is not a class"
            )


class AIWorkflowConfig(models.Model):
    """
    Configuration templates for different AI workflows

    .. no_pii:
    """
    course_id = CourseKeyField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Course associated with this session"
    )

    location_regex = models.CharField(
        max_length=255,
        default=None,
        null=True,
        blank=True,
        help_text="Location regex this config applies to",
    )

    # Orchestrator configuration
    orchestrator_class = models.CharField(
        max_length=255,
        help_text="Full class name of the orchestrator",
        validators=[validate_orchestrator_class],
    )

    # Processor configuration (LLM settings, templates, etc.)
    processor_config = models.JSONField(
        default=dict,
        help_text="LLM provider, model, template settings",
        validators=[validate_processor_config],
    )

    # Actuator configuration (response format, UI components, etc.)
    actuator_config = models.JSONField(
        default=dict, help_text="Response formatting and UI settings"
    )

    service_variant = models.CharField(
        max_length=50,
        choices=[
            ("lms", "LMS"),
            ("cms", "CMS"),
        ],
        default="lms",
        help_text="Service variant to use for this workflow",
    )

    enabled = models.BooleanField(
        default=True, help_text="Whether this workflow configuration is enabled"
    )

    class Meta:
        unique_together = ["course_id", "location_regex", "service_variant"]
        indexes = [
            models.Index(fields=["course_id", "location_regex", "service_variant"]),
        ]

    def __str__(self):
        location_part = (self.location_regex if self.location_regex else "global")
        return f"AIWorkflowConfig for {location_part} [{self.service_variant}]"

    @classmethod
    def get_config(
        cls, course_id: Optional[str] = None, location_id: Optional[str] = None
    ):
        """
        Get configuration for a specific action, course, and location and service variant.

        First tries to find a config with a location_regex that matches the location_id.
        If not found, falls back to a general config for the course (location_regex is null).
        """
        service_variant = getattr(settings, "SERVICE_VARIANT", "lms")

        # First, try to find a config with location_regex matching the location_id
        if location_id:
            # Get all configs for this course and service that have a location_regex
            configs = cls.objects.filter(
                enabled=True,
                service_variant=service_variant,
                course_id=course_id,
                location_regex__isnull=False
            )

            # Check each config's regex against the location_id
            for config in configs:
                try:
                    if re.search(config.location_regex, location_id):
                        return config
                except re.error as e:
                    continue

        # Fallback: try to find a general config (no location_regex)
        try:
            response = cls.objects.get(
                enabled=True,
                service_variant=service_variant,
                course_id=course_id,
                location_regex__isnull=True
            )
            return response
        except cls.DoesNotExist:
            pass

        # Fallback: try to find a global config (no course_id, no location_regex)
        try:
            response = cls.objects.get(
                enabled=True,
                service_variant=service_variant,
                course_id=CourseKeyField.Empty,
                location_regex__isnull=True
            )
            return response
        except cls.DoesNotExist:
            return None


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

    @classmethod
    def find_workflow_for_context(
        cls, action: str, course_id: str, user, context: Dict
    ) -> tuple["AIWorkflow", bool]:
        """
        Find or create workflow based on action, course, user and context
        This is the main entry point for the API

        Returns: (workflow_instance, created_boolean)
        """

        # Extract location_id from context if present
        location_id = context.get("unitId")

        # Get workflow configuration
        config = AIWorkflowConfig.get_config(course_id, location_id)
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
            config=config,  # Asignar directamente
            extra_context=context,
            context_data={},
        )
        created = True

        logger.info(
            f"🤖 WORKFLOW FINDER: {'Created new' if created else 'Found existing'} workflow {workflow.get_natural_key()}"
        )
        return workflow, created

    def execute(self, user_input) -> Dict[str, Any]:
        """
        Execute this workflow using its configured orchestrator
        This is where the actual AI processing happens

        Returns: Dictionary with execution results
        """
        logger.info(
            f"🤖 WORKFLOW EXECUTOR: Starting execution for {self.get_natural_key()}"
        )

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

            logger.info(
                f"🤖 WORKFLOW EXECUTOR: Completed execution for {self.get_natural_key()}, status={self.status}"
            )

            # Add workflow metadata to result
            result.update(
                {
                    "workflow_info": {
                        # 'natural_key': self.get_natural_key(),
                        # 'status': self.status,
                        # 'current_step': self.current_step,
                    }
                }
            )

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
