"""
AI Workflow models for managing flexible AI workflow execution
"""
import logging
import re
from typing import Any, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
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
        null=False,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "Identifier of the UI slot that renders this scope. "
            "Must exactly match the uiSlotSelectorId prop sent by the frontend widget. "
            "The scope only renders when a widget sends this exact value. "
            "Choose from the available options configured in OPENEDX_AI_EXTENSIONS_UI_SLOT_IDS."
        ),
    )

    specificity_index = models.IntegerField(
        default=0,
        editable=False,
        help_text=(
            "Auto-calculated resolution specificity (populated on save). "
            "Weighted sum of non-null discriminator fields: "
            "location_regex (+4) + course_id (+2) + ui_slot_selector_id (+1). "
            "Higher value means more specific and wins in resolution order."
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
    def get_profile(cls, course_id=None, location_id=None, ui_slot_selector_id=None):
        """
        Resolve the best-matching AIWorkflowScope for the given context.

        ``ui_slot_selector_id`` is **required** for a scope to be found. Each frontend
        widget sends its own identifier and only receives the scope explicitly
        configured for that identifier. If no ``ui_slot_selector_id`` is provided,
        or no scope exists for the given value, ``None`` is returned and the widget
        does not render.

        Resolution strategy:

        Phase 1 — DB filter: query all enabled scopes that match
        ``ui_slot_selector_id`` exactly. ``course_id`` and ``location_regex``
        still act as wildcards (NULL = match any). Results are ordered by
        ``specificity_index`` descending so the most specific scope wins.

        Phase 2 — Python regex loop: iterates over ordered candidates and
        returns the first scope whose ``location_regex`` matches ``location_id``
        (or is NULL). The first match wins — no tie-breaking needed.

        Results are cached using functools.lru_cache (max 128 entries).
        Cache is cleared automatically when AIWorkflowScope or AIWorkflowProfile
        objects are saved or deleted.
        """
        if not ui_slot_selector_id:
            # No slot identifier provided — nothing can match.
            return None

        service_variant = getattr(settings, "SERVICE_VARIANT", "lms")

        # Phase 1 — DB filter
        candidates = cls.objects.filter(
            Q(course_id=course_id) | Q(course_id=CourseKeyField.Empty),
            Q(ui_slot_selector_id=ui_slot_selector_id) | Q(ui_slot_selector_id=""),
            enabled=True,
            service_variant=service_variant,
        ).order_by("-specificity_index")

        # Phase 2 — Python regex loop
        for scope in candidates:
            if scope.location_regex is None:
                # NULL location_regex is a wildcard — matches any location
                scope.location_id = location_id
                return scope
            if not location_id:
                # Scope requires a location but none was provided — skip
                continue
            try:
                if re.search(scope.location_regex, location_id):
                    scope.location_id = location_id
                    return scope
            except re.error:
                continue

        return None

    def execute(self, user_input, action, user, running_context) -> dict[str, str | dict[str, str]] | Any:
        """
        Execute this workflow using its configured orchestrator
        This is where the actual AI processing happens

        Returns: Dictionary with execution results
        """
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

    def clean(self):
        """Validate the scope before saving."""
        super().clean()
        if self.location_regex and not self.course_id:
            raise ValidationError({
                "course_id": "Required when location_regex is set.",
            })

    def _compute_specificity_index(self) -> int:
        """Calculate specificity_index using CSS-like weighted scores.

        location_regex (+4) > course_id (+2) > ui_slot_selector_id (+1).
        NULL fields are treated as wildcards and contribute 0 to the score.
        """
        return (
            (4 if self.location_regex else 0)
            + (2 if self.course_id else 0)
            + (1 if self.ui_slot_selector_id else 0)
        )

    def save(self, *args, **kwargs):
        """Override save to compute specificity_index and clear cache on changes."""
        self.specificity_index = self._compute_specificity_index()
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
