"""
Serializers for AI Workflows API
"""

import copy

from rest_framework import serializers

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


class AIWorkflowProfileListSerializer(serializers.Serializer):
    """
    Serializer for a single AIWorkflowProfile in the profiles list endpoint.

    Exposes the profile's identity fields and its complete effective
    configuration with sensitive values redacted. Designed to be extended
    in future iterations to expose globally-configured provider information
    alongside profile-level settings.
    """

    id = serializers.UUIDField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    description = serializers.CharField(allow_null=True, read_only=True)
    effective_config = serializers.SerializerMethodField()

    def get_effective_config(self, obj):
        """Return effective config with sensitive values redacted."""
        config = obj.config or {}
        return redact_sensitive_config(config)

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("AIWorkflowProfileListSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("AIWorkflowProfileListSerializer is read-only")
