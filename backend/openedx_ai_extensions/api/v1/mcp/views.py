"""
MCP Server HTTP Views.

This module provides Django REST Framework views for handling MCP server HTTP requests.
Adapted from django-mcp-server by Omar BENHAMID (https://github.com/gts360/django-mcp-server).
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from openedx_ai_extensions.mcp.server import mcp


# Extracted/adapted from django-mcp-server by Omar BENHAMID (https://github.com/gts360/django-mcp-server)
# Copyright (c) 2025 Omar BENHAMID
# Licensed under the MIT License
@method_decorator(csrf_exempt, name='dispatch')
class MCPServerStreamableHttpView(APIView):
    """
    Django REST Framework view for handling MCP server HTTP requests.

    Provides GET and POST endpoints that forward requests to the MCP server.
    """
    mcp_server = mcp

    def get(self, request, *args, **kwargs):
        return self.mcp_server.handle_django_request(request)

    def post(self, request, *args, **kwargs):
        return self.mcp_server.handle_django_request(request)
