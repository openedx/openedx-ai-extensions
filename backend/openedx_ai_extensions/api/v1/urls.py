"""
Version 1 API URLs
"""

from django.urls import path

from openedx_ai_extensions.mcp.server import mcp

from .mcp.views import MCPServerStreamableHttpView
from .workflows.views import AIGenericWorkflowView, AIWorkflowConfigView

app_name = "v1"

urlpatterns = [
    path("workflows/", AIGenericWorkflowView.as_view(), name="aiext_workflows"),
    path("config/", AIWorkflowConfigView.as_view(), name="aiext_ui_config"),
    path("mcp", MCPServerStreamableHttpView.as_view(mcp_server=mcp), name="mcp_server"),
]
