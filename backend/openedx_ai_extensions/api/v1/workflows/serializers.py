"""
Serializers for AI Workflows API
"""

import copy

from rest_framework import serializers

from openedx_ai_extensions.models import PromptTemplate

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

    Exposes all public fields of the template.
    """

    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    body = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

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
    with sensitive values redacted, and the list of scopes that link to it in
    the current request context. Designed to be extended in future iterations
    to expose globally-configured provider information alongside profile-level
    settings.
    """

    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    description = serializers.CharField(allow_null=True, read_only=True)
    effective_config = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()

    def get_effective_config(self, obj):
        """Return effective config with sensitive values redacted."""
        config = obj.config or {}
        return redact_sensitive_config(config)

    def get_scopes(self, obj):
        """Return all scopes that matched this profile in the request context."""
        matched_scopes = getattr(obj, "matched_scopes", [])
        return AIWorkflowScopeSerializer(matched_scopes, many=True).data

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("AIWorkflowProfileListSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("AIWorkflowProfileListSerializer is read-only")
