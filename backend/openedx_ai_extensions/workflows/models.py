"""
AI Workflow models for managing flexible AI workflow execution
"""

import logging
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from openedx_ai_extensions.utils import emit_event

from openedx_ai_extensions.workflows import orchestrators
from openedx_ai_extensions.workflows.processors.xapi.constants import EVENT_NAME_WORKFLOW_COMPLETED

User = get_user_model()
logger = logging.getLogger(__name__)


class AIWorkflowConfig(models.Model):
    """
    Configuration templates for different AI workflows
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
    def get_config(cls, action: str, course_id: Optional[str] = None):
        """Get the best matching configuration for action and course"""
        # Returns fixed in memory object for now
        return cls(
            action=action,
            course_id=course_id,
            orchestrator_class="DirectLLMResponse",
            # orchestrator_class="MockResponse",
            processor_config={
                "OpenEdXProcessor": {
                    "function": "get_unit_content",
                    "char_limit": 300,
                },
                'LLMProcessor': {
                    'function': "explain_like_five",
                    'config': "default",
                },
            },
            actuator_config={},  # TODO: first I must make the actuator selection dynamic
        )


class AIWorkflow(models.Model):
    """
    Individual AI workflow instances with state management
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
    unit_id = models.CharField(
        max_length=255, null=True, blank=True, help_text="Unit context"
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
        unique_together = ["user", "action", "course_id", "unit_id"]
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
            parts.append(self.course_id)
        if self.unit_id:
            parts.append(self.unit_id)
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
        logger.info(
            f"🤖 WORKFLOW FINDER: Looking for workflow action='{action}', course='{course_id}', user='{user.username}'"
        )

        # Extract unit_id from context if present
        unit_id = context.get("unitId")

        # Get workflow configuration
        config = AIWorkflowConfig.get_config(action, course_id)
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
            unit_id=unit_id,
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
            orchestrator_name = self.config.orchestrator_class  # "DirectLLMResponse"
            orchestrator = getattr(orchestrators, orchestrator_name)(workflow=self)

            # Execute the orchestrator
            result = orchestrator.run(user_input)

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

            event_data = {
                "workflow_id": self.get_natural_key(),
                "action": self.action,
                "course_id": self.course_id,
            }

            emit_event(EVENT_NAME_WORKFLOW_COMPLETED, self.course_id, event_data)

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
                    'current_step': self.current_step
                },
            }

    def _load_orchestrator(self):
        """Load the orchestrator for this workflow"""
        # This method is currently unused - orchestrator loading happens in execute()
        # TODO: Refactor to use this method or remove it
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
        self.current_step = 'completed'  # pylint: disable=attribute-defined-outside-init
        self.completed_at = timezone.now()
        if final_context:
            self.context_data.update(final_context)
        # self.save(update_fields=['status', 'current_step', 'completed_at', 'context_data', 'updated_at'])
