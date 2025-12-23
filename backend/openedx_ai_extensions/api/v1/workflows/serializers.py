"""
Serializers for AI Workflows API
"""

from rest_framework import serializers


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
