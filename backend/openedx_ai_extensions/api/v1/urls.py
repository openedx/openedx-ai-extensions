"""
Version 1 API URLs
"""

from django.urls import path

from openedx_ai_extensions.mcp.server import mcp

from .mcp.views import MCPServerStreamableHttpView
from .pipelines.views import AIGenericWorkflowView

app_name = "v1"

urlpatterns = [
    path("workflows/", AIGenericWorkflowView.as_view(), name="ai_pipelines"),
    path("mcp", MCPServerStreamableHttpView.as_view(mcp_server=mcp), name="mcp_server"),
]
