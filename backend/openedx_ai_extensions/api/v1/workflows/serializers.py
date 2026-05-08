"""
Serializers for AI Workflows API
"""

import copy

from django.db.models import Q
from rest_framework import serializers

from openedx_ai_extensions.models import PromptTemplate
from openedx_ai_extensions.workflows.models import AIWorkflowProfile

# Keys whose values must never be exposed to the frontend.
_SENSITIVE_KEYS = frozenset({
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
})


def redact_sensitive_config(config):
    """
    Return a deep copy of config with sensitive leaf values redacted.

    Recursively walks nested dicts and lists. Any dict key that matches
    a name in ``_SENSITIVE_KEYS`` (case-insensitive) has its value replaced
    with the string ``"[REDACTED]"``.

    Args:
        config (dict): Workflow effective configuration dict.

    Returns:
        dict: New dict with sensitive values replaced.
    """
    config_copy = copy.deepcopy(config)
    return _redact_node(config_copy)


def _redact_node(node):
    """
    Recursively redact sensitive keys from a dict or list node.

    Args:
        node: A dict, list, or scalar value.

    Returns:
        The node with sensitive values replaced.
    """
    if isinstance(node, dict):
        for key in node:
            if key.lower() in _SENSITIVE_KEYS:
                node[key] = "[REDACTED]"
            else:
                node[key] = _redact_node(node[key])
    elif isinstance(node, list):
        for i, item in enumerate(node):
            node[i] = _redact_node(item)
    return node


class PromptTemplateSerializer(serializers.Serializer):
    """
    Serializer for a PromptTemplate instance.

    Exposes all public fields of the template plus a ``usage`` object that counts
    how many AIWorkflowProfile configs reference this template.
    """

    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    body = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    usage = serializers.SerializerMethodField()

    def get_usage(self, obj):
        """
        Count how many AIWorkflowProfile configs reference this template.

        Phase 1 — DB text search: filter profiles whose ``content_patch`` contains
        the template slug or UUID string (fast LIKE/ILIKE, no disk reads).
        Phase 2 — effective-config check: compute the merged config only for those
        candidates and confirm the reference is in ``processor_config``.

        Returns ``{"profile_count": None}`` if the count cannot be determined, so
        callers can distinguish "zero uses" from "unknown" without a 500.
        """
        try:
            slug = obj.slug
            uuid_str = str(obj.id)

            candidates = AIWorkflowProfile.objects.filter(
                Q(content_patch__icontains=slug) | Q(content_patch__icontains=uuid_str),
                content_patch__icontains="prompt_template",
            )

            count = 0
            for profile in candidates:
                try:
                    config = profile.config or {}
                except Exception:  # pylint: disable=broad-exception-caught
                    continue
                processor_config = config.get("processor_config") or {}
                if not isinstance(processor_config, dict):
                    continue
                for processor in processor_config.values():
                    if not isinstance(processor, dict):
                        continue
                    template_ref = processor.get("prompt_template")
                    if template_ref and (
                        str(template_ref) == uuid_str or str(template_ref) == slug
                    ):
                        count += 1
                        break
            return {"profile_count": count}
        except Exception:  # pylint: disable=broad-exception-caught
            return {"profile_count": None}

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("PromptTemplateSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("PromptTemplateSerializer is read-only")


class PromptTemplateUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer for PromptTemplate — only ``body`` may be changed.

    Any field other than ``body`` in the request payload is rejected with a
    validation error. ``created_at`` and ``updated_at`` are managed by Django
    automatically and are never accepted as input.
    """

    class Meta:
        """Serializer metadata."""

        model = PromptTemplate
        fields = ["body"]

    def validate(self, attrs):
        """Reject any field not in the allowed set."""
        allowed = {"body"}
        extra = set(self.initial_data.keys()) - allowed
        if extra:
            raise serializers.ValidationError(
                {field: "This field cannot be changed." for field in extra}
            )
        return super().validate(attrs)


class AIWorkflowProfileSerializer(serializers.Serializer):
    """
    Serializer for AIWorkflowProfile data
    Simple serializer to pass profile config from backend to frontend
    Exposes only the UIComponents dict from the profile
    """

    course_id = serializers.CharField(allow_null=True, required=False)
    ui_components = serializers.SerializerMethodField()

    def get_ui_components(self, obj):
        """Extract UIComponents from actuator_config"""
        return obj.profile.get_ui_components()

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("AIWorkflowProfileSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("AIWorkflowProfileSerializer is read-only")


class AIWorkflowScopeSerializer(serializers.Serializer):
    """
    Serializer for an AIWorkflowScope instance in the profiles list endpoint.

    Exposes the routing fields that caused a scope to match the request context.
    """

    id = serializers.UUIDField(read_only=True)
    course_id = serializers.CharField(allow_null=True, read_only=True)
    service_variant = serializers.CharField(read_only=True)
    enabled = serializers.BooleanField(read_only=True)
    ui_slot_selector_id = serializers.CharField(read_only=True)
    location_regex = serializers.CharField(allow_null=True, read_only=True)
    specificity_index = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("AIWorkflowScopeSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("AIWorkflowScopeSerializer is read-only")


class AIWorkflowProfileListSerializer(serializers.Serializer):
    """
    Serializer for a single AIWorkflowProfile in the profiles list endpoint.

    Exposes the profile's identity fields, its complete effective configuration
    with sensitive values redacted, the list of scopes that link to it in the
    current request context, and a ``usage`` object with the total scope count
    across all courses and contexts.
    """

    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    description = serializers.CharField(allow_null=True, read_only=True)
    effective_config = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()

    def get_effective_config(self, obj):
        """Return effective config with sensitive values redacted."""
        config = obj.config or {}
        return redact_sensitive_config(config)

    def get_scopes(self, obj):
        """Return all scopes that matched this profile in the request context."""
        matched_scopes = getattr(obj, "matched_scopes", [])
        return AIWorkflowScopeSerializer(matched_scopes, many=True).data

    def get_usage(self, obj):
        """Return total number of scopes pointing to this profile across all contexts."""
        return {"scope_count": obj.aiworkflowscope_set.count()}

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("AIWorkflowProfileListSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("AIWorkflowProfileListSerializer is read-only")
