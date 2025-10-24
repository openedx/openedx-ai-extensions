"""
Version 1 API URLs
"""

from django.urls import path

from .pipelines.views import AIGenericWorkflowView

app_name = "v1"

urlpatterns = [
    path("workflows/", AIGenericWorkflowView.as_view(), name="ai_pipelines"),
]
