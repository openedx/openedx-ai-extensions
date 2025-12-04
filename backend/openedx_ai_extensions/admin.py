"""
Django admin configuration for AI Extensions models.
"""

from django.contrib import admin

from openedx_ai_extensions.workflows.models import AIWorkflowConfig, AIWorkflowSession


@admin.register(AIWorkflowSession)
class AIWorkflowSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing AI Workflow Sessions.
    """

    list_display = (
        "user",
        "course_id",
        "location_id",
    )
    search_fields = ("user__username", "course_id", "location_id")
    readonly_fields = ("local_submission_id", "remote_response_id", "metadata")


@admin.register(AIWorkflowConfig)
class AIWorkflowConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for managing AI Workflow Configurations.
    """

    list_display = (
        "course_id",
        "location_regex",
        "orchestrator_class",
        "service_variant",
        "enabled",
    )
    search_fields = ("course_id", "location_regex", "orchestrator_class")
    list_filter = ("service_variant", "enabled")
