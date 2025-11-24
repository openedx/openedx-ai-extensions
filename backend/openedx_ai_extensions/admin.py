"""
Django admin configuration for AI Extensions models.
"""

from django.contrib import admin

from openedx_ai_extensions.workflows.models import AIWorkflowSession


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
