"""
Main API URLs for openedx-ai-extensions
"""

from django.urls import include, path
from mcp_server.views import MCPServerStreamableHttpView

from ..mcp.server import mcp

app_name = "openedx_ai_extensions_api"

urlpatterns = [
    path("v1/", include("openedx_ai_extensions.api.v1.urls", namespace="v1")),
    path("mcp", MCPServerStreamableHttpView.as_view(mcp_server=mcp), name="mcp_server"),
]
