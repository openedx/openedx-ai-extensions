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

from openedx_ai_extensions.workflows.orchestrators import BaseOrchestrator
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

    def clean(self):
        """Validate the effective configuration before saving."""
        super().clean()
        effective_config = get_effective_config(self.base_filepath, self.content_patch_dict)
        if effective_config is not None:
            is_valid, errors = validate_workflow_config(effective_config)
            if not is_valid:
                raise ValidationError({
                    "content_patch": errors,
                })

    def save(self, *args, **kwargs):
        """Override save to validate and clear cached config."""
        self.full_clean()
        # Invalidate cached_property so it's recomputed after save
        self.__dict__.pop("config", None)
        super().save(*args, **kwargs)


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

    ui_slot_selector_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Identifier of the UI slot that renders this scope. "
            "Required when multiple scopes share the same location. "
            "Must match the uiSlotSelectorId prop passed by the frontend widget."
        ),
    )

    priority = models.IntegerField(
        default=0,
        help_text=(
            "Resolution priority when multiple scopes match the same location_regex and ui_slot_selector_id. "
            "Higher value wins. Scopes with equal priority and equal matches raise an error."
        ),
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
    def get_profile(cls, course_id=None, location_id=None, ui_slot_selector_id=None):
        """
        Get configuration for a specific action, course, location, ui_slot and service variant.

        First tries to find a config with a location_regex that matches the location_id.
        If not found, falls back to a general config for the course (location_regex is null).

        Results are cached using functools.lru_cache (max 128 entries).
        Cache is automatically cleared when AIWorkflowScope or AIWorkflowProfile objects change.
        """
        service_variant = getattr(settings, "SERVICE_VARIANT", "lms")

        if ui_slot_selector_id:
            return cls._get_profile_for_ui_slot(
                course_id=course_id,
                location_id=location_id,
                ui_slot_selector_id=ui_slot_selector_id,
                service_variant=service_variant,
            )

        if location_id:
            legacy_profile = cls._get_profile_legacy(
                course_id=course_id,
                location_id=location_id,
                service_variant=service_variant,
            )
            if legacy_profile is not None:
                return legacy_profile

            slot_fallback = cls._get_profile_slot_fallback(
                course_id=course_id,
                location_id=location_id,
                service_variant=service_variant,
            )
            if slot_fallback is not None:
                return slot_fallback

        # Fallback: general config for the course (no location_regex, no ui_slot_selector_id)
        try:
            response = cls.objects.get(
                enabled=True,
                service_variant=service_variant,
                course_id=course_id,
                location_regex__isnull=True,
                ui_slot_selector_id__isnull=True,
            )
            return response
        except cls.DoesNotExist:
            pass

        # Fallback: global config (no course_id, no location_regex, no ui_slot_selector_id)
        try:
            response = cls.objects.get(
                enabled=True,
                service_variant=service_variant,
                course_id=CourseKeyField.Empty,
                location_regex__isnull=True,
                ui_slot_selector_id__isnull=True,
            )
            return response
        except cls.DoesNotExist:
            return None

    @classmethod
    def _matches_location(cls, scope, location_id) -> bool:
        """Return True if the scope matches the provided location_id.

        If scope has a location_regex, it must compile and match location_id.
        Regex errors are treated as non-matches.
        """
        if scope.location_regex:
            if not location_id:
                return False
            try:
                return bool(re.search(scope.location_regex, location_id))
            except re.error:
                return False
        return True

    @classmethod
    def _get_profile_for_ui_slot(cls, course_id, location_id, ui_slot_selector_id, service_variant):
        """Resolve a scope for a given ui_slot_selector_id.

        Returns the highest-priority matching scope. Raises ValueError if none match
        or if there is an equal-priority tie.
        """
        candidates = cls.objects.filter(
            enabled=True,
            service_variant=service_variant,
            ui_slot_selector_id=ui_slot_selector_id,
            course_id=course_id,
        )

        matching = []
        for scope in candidates:
            if not cls._matches_location(scope, location_id):
                continue
            scope.location_id = location_id
            matching.append(scope)

        if not matching:
            raise ValueError(
                f"No AIWorkflowScope found for ui_slot_selector_id='{ui_slot_selector_id}', "
                f"course_id='{course_id}', location_id='{location_id}'. "
                "Make sure a scope with a matching ui_slot_selector_id exists and is enabled."
            )

        matching.sort(key=lambda s: s.priority, reverse=True)
        if len(matching) > 1 and matching[0].priority == matching[1].priority:
            raise ValueError(
                f"Multiple AIWorkflowScope entries tie for ui_slot_selector_id='{ui_slot_selector_id}' "
                f"at location '{location_id}' with equal priority {matching[0].priority}. "
                "Assign distinct priorities to resolve the ambiguity."
            )

        return matching[0]

    @classmethod
    def _get_profile_legacy(cls, course_id, location_id, service_variant):
        """Resolve a legacy scope (ui_slot_selector_id is NULL) for location_id.

        Returns a single matching legacy scope, None if no legacy matches, and
        raises ValueError if multiple legacy scopes match the same location.
        """
        configs = cls.objects.filter(
            enabled=True,
            service_variant=service_variant,
            location_regex__isnull=False,
            ui_slot_selector_id__isnull=True,
            course_id=course_id,
        )

        selected_config = None
        for config in configs:
            try:
                if re.search(config.location_regex, location_id):
                    config.location_id = location_id
                    if selected_config is None:
                        selected_config = config
                    else:
                        raise ValueError(
                            f"Multiple AIWorkflowScope configs match location_id '{location_id}': "
                            f"'{selected_config.id}' and '{config.id}'. "
                            "Set a ui_slot_selector_id on each scope to support multiple scopes per location."
                        )
            except re.error:
                continue

        return selected_config

    @classmethod
    def _get_profile_slot_fallback(cls, course_id, location_id, service_variant):
        """Graceful fallback when no selector-id was provided.

        If exactly one selector-id scope matches the location, return it.
        If multiple selector-id scopes match, raise ValueError to force
        disambiguation via uiSlotSelectorId.
        """
        configs_with_slot = cls.objects.filter(
            enabled=True,
            service_variant=service_variant,
            location_regex__isnull=False,
            ui_slot_selector_id__isnull=False,
            course_id=course_id,
        )

        slot_matches = []
        for config in configs_with_slot:
            try:
                if re.search(config.location_regex, location_id):
                    config.location_id = location_id
                    slot_matches.append(config)
            except re.error:
                continue

        if len(slot_matches) == 1:
            return slot_matches[0]

        if len(slot_matches) > 1:
            raise ValueError(
                f"Multiple AIWorkflowScope entries match location_id '{location_id}' "
                "and no uiSlotSelectorId was provided to disambiguate. "
                "Pass a uiSlotSelectorId from the frontend widget to select the correct scope."
            )

        return None

    def execute(self, user_input, action, user, running_context) -> dict[str, str | dict[str, str]] | Any:
        """
        Execute this workflow using its configured orchestrator
        This is where the actual AI processing happens

        Returns: Dictionary with execution results
        """

        try:
            # Load the orchestrator for this workflow
            orchestrator = BaseOrchestrator.get_orchestrator(
                workflow=self,
                user=user,
                context=running_context,
            )

            self.action = action

            if not hasattr(orchestrator, action):
                raise NotImplementedError(
                    f"Orchestrator '{self.profile.orchestrator_class}' does not implement action '{action}'"
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

        # Guard against duplicate legacy (NULL ui_slot_selector_id) scopes for the
        # same course + location_regex.  A scope with a ui_slot_selector_id is always
        # allowed to coexist with legacy scopes so the frontend can opt-in via the
        # slot selector while old integrations continue to use the legacy path.
        if self.location_regex and self.course_id and not self.ui_slot_selector_id:
            legacy_siblings = AIWorkflowScope.objects.filter(
                course_id=self.course_id,
                location_regex=self.location_regex,
                enabled=True,
                ui_slot_selector_id__isnull=True,
            ).exclude(pk=self.pk)

            if legacy_siblings.exists():
                raise ValidationError({
                    "ui_slot_selector_id": (
                        "A legacy scope (no ui_slot_selector_id) already exists for this "
                        "course + location_regex combination. "
                        "Set a unique ui_slot_selector_id on both scopes so each frontend "
                        "widget can resolve exactly one scope."
                    ),
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
        unique_together = ("user", "scope", "profile", "course_id", "location_id")

    def get_local_thread(self):
        """
        Fetch the full local conversation thread from submissions.

        Returns:
            list or None: Messages in chronological order, or None if no submission exists.
        """
        # pylint: disable=import-outside-toplevel
        from openedx_ai_extensions.processors.openedx.submission_processor import SubmissionProcessor

        if not self.local_submission_id:
            return None

        processor = SubmissionProcessor(
            config=self.profile.processor_config if self.profile else {},
            user_session=self,
        )
        return processor.get_full_thread()

    def get_remote_thread(self):
        """
        Fetch the full remote conversation thread from the LLM provider via LiteLLM.

        Instantiates an LLMProcessor with the profile's processor config so that
        provider credentials (api_key, api_base, etc.) are resolved and passed through.

        Returns:
            list or None: Chronologically ordered response dicts, or None if no remote ID exists.
        """
        from openedx_ai_extensions.processors.llm.llm_processor import (  # pylint: disable=import-outside-toplevel
            LLMProcessor,
        )

        if not self.remote_response_id:
            return None

        processor = LLMProcessor(
            config=self.profile.processor_config if self.profile else {},
            user_session=self,
        )
        return processor.fetch_remote_thread(self.remote_response_id)

    def get_combined_thread(self):  # pylint: disable=too-many-statements
        """
        Build a unified chronological thread combining local and remote data.

        The remote thread is the backbone (it has system messages, reasoning,
        tool calls). Local thread enriches with submission_id and timestamp.
        Messages are deduplicated across responses since each remote response's
        input replays the full history.

        Returns:
            list or None: Flat list of message dicts with all available metadata.
        """
        local_thread = self.get_local_thread()
        remote_thread = self.get_remote_thread()

        if not remote_thread:
            return local_thread

        # Build lookup from local thread: (role, content_prefix) -> local msg
        local_by_content = {}
        if local_thread:
            for msg in local_thread:
                role = msg.get("role", "")
                content = msg.get("content", "")
                content_str = content if isinstance(content, str) else str(content)
                key = (role, content_str[:200])
                # Keep the last match (most recent submission_id)
                local_by_content[key] = msg

        combined = []
        seen = set()

        for response in remote_thread:
            if not isinstance(response, dict):
                continue

            if "error" in response:
                combined.append({
                    "role": "error",
                    "type": "error",
                    "content": response.get("error", "Unknown error"),
                    "response_id": response.get("id"),
                })
                continue

            response_meta = {
                "response_id": response.get("id", "unknown"),
                "created_at": response.get("created_at"),
                "model": response.get("model"),
            }

            # Process input items (system, user, reasoning, tool results, etc.)
            for item in response.get("input", []):
                content = item.get("content", "")
                content_str = content if isinstance(content, str) else str(content)
                content_key = (item.get("role", ""), content_str[:200])
                if content_key in seen:
                    continue
                seen.add(content_key)

                msg = {
                    "role": item.get("role", "unknown"),
                    "type": item.get("type", "message"),
                    "content": content,
                    "source": "remote",
                    **response_meta,
                }

                # Enrich with local metadata
                local_key = (item.get("role", ""), content_str[:200])
                if local_key in local_by_content:
                    local_msg = local_by_content.pop(local_key)
                    msg["timestamp"] = local_msg.get("timestamp")
                    msg["submission_id"] = local_msg.get("submission_id")
                    msg["source"] = "both"

                combined.append(msg)

            # Process output items (assistant responses, tool calls)
            for item in response.get("output", []):
                content = item.get("content", "")
                content_str = content if isinstance(content, str) else str(content)
                content_key = (item.get("role", ""), content_str[:200])
                seen.add(content_key)

                msg = {
                    "role": item.get("role", "unknown"),
                    "type": item.get("type", "message"),
                    "content": content,
                    "source": "remote",
                    "tokens": response.get("tokens"),
                    **response_meta,
                }
                # Pass through structured fields for tool-call items.
                msg.update({k: item[k] for k in ("name", "arguments", "call_id") if item.get(k) is not None})

                local_key = (item.get("role", ""), content_str[:200])
                if local_key in local_by_content:
                    local_msg = local_by_content.pop(local_key)
                    msg["timestamp"] = local_msg.get("timestamp")
                    msg["submission_id"] = local_msg.get("submission_id")
                    msg["source"] = "both"

                combined.append(msg)

        # Insert any local-only messages at their correct chronological position
        for local_msg in local_by_content.values():
            entry = {
                **local_msg,
                "type": "message",
                "source": "local",
            }
            ts = str(local_msg.get("timestamp", ""))
            # Find the right position: before the first message with a later timestamp
            insert_at = len(combined)
            for i, existing in enumerate(combined):
                existing_ts = str(existing.get("timestamp") or existing.get("created_at") or "")
                if existing_ts and ts and existing_ts > ts:
                    insert_at = i
                    break
            combined.insert(insert_at, entry)

        return combined


# Signal handlers for cache invalidation
@receiver(post_save, sender=AIWorkflowScope)
@receiver(post_delete, sender=AIWorkflowScope)
@receiver(post_save, sender=AIWorkflowProfile)
@receiver(post_delete, sender=AIWorkflowProfile)
def clear_workflow_cache(**kwargs):
    """
    Clear get_profile LRU cache when AIWorkflowScope or AIWorkflowProfile objects change.
    This ensures the cache stays fresh when workflow configurations are modified.
    """
    AIWorkflowScope.get_profile.cache_clear()
