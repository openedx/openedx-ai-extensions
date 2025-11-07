"""
Serializers for AI Workflows API
"""

from rest_framework import serializers


class AIWorkflowConfigSerializer(serializers.Serializer):
    """
    Serializer for AIWorkflowConfig data
    Simple serializer to pass config from backend to frontend
    Exposes only the UIComponents dict from actuator_config
    """

    action = serializers.CharField()
    course_id = serializers.CharField(allow_null=True, required=False)
    ui_components = serializers.SerializerMethodField()

    def get_ui_components(self, obj):
        """Extract UIComponents from actuator_config"""
        actuator_config = obj.actuator_config or {}
        return actuator_config.get('UIComponents', {})

    def create(self, validated_data):
        """Read-only serializer — creation not supported."""
        raise NotImplementedError("AIWorkflowConfigSerializer is read-only")

    def update(self, instance, validated_data):
        """Read-only serializer — update not supported."""
        raise NotImplementedError("AIWorkflowConfigSerializer is read-only")
