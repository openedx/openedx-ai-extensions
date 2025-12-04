"""
Version 1 API URLs
"""

from django.urls import include, path

from .workflows.views import AIGenericWorkflowView, AIWorkflowConfigView
from .processors.views import OpenEdXProcessorView

app_name = "v1"

urlpatterns = [
    path("workflows/", AIGenericWorkflowView.as_view(), name="aiext_workflows"),
    path("config/", AIWorkflowConfigView.as_view(), name="aiext_ui_config"),
    path("processors/openedxprocessor", OpenEdXProcessorView.as_view(), name="openedx_processor"),
]
