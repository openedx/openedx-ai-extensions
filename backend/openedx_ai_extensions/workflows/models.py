"""
AI Workflow models for managing flexible AI workflow execution
"""
import functools
import logging
import re
from typing import Any, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

from openedx_ai_extensions.workflows.template_utils import (
    get_effective_config,
    parse_json5_string,
    validate_workflow_config,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class AIWorkflowProfile(models.Model):
    """
    Workflow profile combining a disk-based template with database overrides.

    Templates are read-only JSON files on disk (versioned, immutable).
    Profiles point to a template and store JSON patch overrides in the DB.
    Effective config = merge(base_template, content_patch)

    .. no_pii:
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.SlugField(
        max_length=255,
        help_text=(
            "Human readable identifier for the AI workflow profile "
            "(lowercase, hyphens allowed). Used for analytics."
        ),
        unique=True
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Description of the AI workflow profile"
    )
    base_filepath = models.CharField(
        max_length=1024,
        help_text="Relative path to base template file (e.g., 'educator_assistant/quiz_generator.json')"
    )
    content_patch = models.TextField(
        blank=True,
        default="",
        help_text="JSON5 Merge Patch (RFC 7386) to apply to base template. Supports comments and trailing commas."
    )

    class Meta:
        verbose_name = "AI Workflow Profile"
        verbose_name_plural = "AI Workflow Profiles"

    def __str__(self):
        return f"{self.slug} ({self.base_filepath})"

    @property
    def content_patch_dict(self) -> dict:
        """
        Parse content_patch as JSON5 and return as dict.

        Returns:
            Parsed dict from JSON5 string, or empty dict if empty/invalid
        """
        if not self.content_patch or not self.content_patch.strip():
            return {}

        try:
            return parse_json5_string(self.content_patch)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error parsing content_patch for {self.slug}: {e}")
            return {}

    @cached_property
    def config(self) -> dict:
        """
        Get the effective configuration by merging base template with overrides.

        Cached per instance to avoid repeated disk reads and merging.

        Returns:
            Merged configuration dict
        """
        return get_effective_config(self.base_filepath, self.content_patch_dict)

    def get_config(self) -> dict:
        """
        Get the effective configuration (backward compatibility).

        Use .config property instead for better performance.
        """
        return self.config

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the effective configuration.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        return validate_workflow_config(self.config)

    def get_ui_components(self) -> dict:
        """Extract UIComponents from the effective configuration."""
        if self.config is None:
            return {}
        actuator_config = self.config.get("actuator_config", {})
        return actuator_config.get("UIComponents", {})

    @property
    def orchestrator_class(self) -> Optional[str]:
        """Get orchestrator class name from effective config."""
        if self.config is None:
            return None
        return self.config.get("orchestrator_class")

    @property
    def processor_config(self) -> dict:
        """Get processor config from effective config."""
        if self.config is None:
            return {}
        return self.config.get("processor_config", {})


class AIWorkflowScope(models.Model):
    """
    .. no_pii:
    """

    _location_id = None
    _action = None

    SERVICE_VARIANTS = [
        ("lms", "LMS"),
        ("cms", "CMS - Studio"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    location_regex = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Regex pattern to match location IDs for this configuration",
    )

    course_id = CourseKeyField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Course associated with this session"
    )

    service_variant = models.CharField(
        max_length=10,
        choices=SERVICE_VARIANTS,
        default="lms",
        help_text="Service variant where this workflow applies",
    )

    profile = models.ForeignKey(
        AIWorkflowProfile,
        on_delete=models.CASCADE,
        help_text="AI workflow profile associated with this configuration",
    )

    enabled = models.BooleanField(
        default=True, help_text="Indicates if this workflow configuration is enabled"
    )

    def __str__(self):
        return f"AIWorkflowScope {self.id} for course {self.course_id} at location {self.location_regex}"

    @property
    def location_id(self):
        """Get the runtime location_id if set."""
        return self._location_id

    @location_id.setter
    def location_id(self, value):
        """Set the runtime location_id."""
        self._location_id = value

    @property
    def action(self):
        """Get the runtime action if set."""
        return self._action

    @action.setter
    def action(self, value):
        """Set the runtime action."""
        self._action = value

    @classmethod
    @functools.lru_cache(maxsize=128)
    def get_profile(cls, course_id, location_id):
        """
        Get configuration for a specific action, course, and location and service variant.

        First tries to find a config with a location_regex that matches the location_id.
        If not found, falls back to a general config for the course (location_regex is null).

        Results are cached using functools.lru_cache (max 128 entries).
        Cache is automatically cleared when AIWorkflowScope or AIWorkflowProfile objects change.
        """
        service_variant = getattr(settings, "SERVICE_VARIANT", "lms")

        # First, try to find a config with location_regex matching the location_id
        if location_id:

            # Get all configs for this course and service that have a location_regex
            configs = cls.objects.filter(
                enabled=True,
                service_variant=service_variant,
                location_regex__isnull=False,
                course_id=course_id,
            )

            # Check each config's regex against the location_id
            selected_config = None
            for config in configs:
                try:
                    if re.search(config.location_regex, location_id):
                        config.location_id = location_id  # Attach for reference
                        if selected_config is None:
                            selected_config = config
                        else:
                            raise ValueError(
                                f"Multiple AIWorkflowScope configs match location_id '{location_id}': "
                                f"'{selected_config.id}' and '{config.id}'"
                            )
                except re.error:
                    continue

            if selected_config:
                return selected_config

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

    def execute(self, user_input, action, user, running_context) -> dict[str, str | dict[str, str]] | Any:
        """
        Execute this workflow using its configured orchestrator
        This is where the actual AI processing happens

        Returns: Dictionary with execution results
        """

        try:
            # Load the orchestrator for this workflow
            from openedx_ai_extensions.workflows import orchestrators  # pylint: disable=import-outside-toplevel

            orchestrator_name = self.profile.orchestrator_class  # "DirectLLMResponse"
            orchestrator_class = getattr(orchestrators, orchestrator_name)
            orchestrator = orchestrator_class(workflow=self, user=user, context=running_context)

            self.action = action

            if not hasattr(orchestrator, action):
                raise NotImplementedError(
                    f"Orchestrator '{orchestrator_name}' does not implement action '{action}'"
                )
            result = getattr(orchestrator, action)(user_input)

            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            return {
                "error": f"Workflow execution failed: {str(e)}",
                "status": "error",
            }

    def clean(self):
        super().clean()
        if self.location_regex and not self.course_id:
            raise ValidationError({
                "course_id": "Required when location_regex is set.",
            })

    def save(self, *args, **kwargs):
        """Override save to clear cache on changes."""
        self.full_clean()
        super().save(*args, **kwargs)


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
    scope = models.ForeignKey(
        AIWorkflowScope,
        on_delete=models.CASCADE,
        help_text="AI workflow scope associated with this session",
    )
    profile = models.ForeignKey(
        AIWorkflowProfile,
        on_delete=models.CASCADE,
        help_text="AI workflow profile associated with this session",
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

    class Meta:
        unique_together = ("user", "scope", "profile")


# Signal handlers for cache invalidation
@receiver(post_save, sender=AIWorkflowScope)
@receiver(post_delete, sender=AIWorkflowScope)
@receiver(post_save, sender=AIWorkflowProfile)
@receiver(post_delete, sender=AIWorkflowProfile)
def clear_workflow_cache(**kwargs):  # pylint: disable=unused-argument
    """
    Clear get_profile LRU cache when AIWorkflowScope or AIWorkflowProfile objects change.
    This ensures the cache stays fresh when workflow configurations are modified.
    """
    AIWorkflowScope.get_profile.cache_clear()
