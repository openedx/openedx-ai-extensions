"""
Version 1 API URLs
"""

from django.urls import path

from .workflows.views import AIGenericWorkflowView, AIWorkflowProfileView

app_name = "v1"

urlpatterns = [
    path("workflows/", AIGenericWorkflowView.as_view(), name="aiext_workflows"),
    path("config/", AIWorkflowProfileView.as_view(), name="aiext_ui_config"),
]
