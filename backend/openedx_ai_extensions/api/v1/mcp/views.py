from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView

from openedx_ai_extensions.mcp.server import mcp


# Extracted/adapted from django-mcp-server by Omar BENHAMID (https://github.com/gts360/django-mcp-server)
# Copyright (c) 2025 Omar BENHAMID
# Licensed under the MIT License
@method_decorator(login_required, name="dispatch")
class MCPServerStreamableHttpView(APIView):
    mcp_server = mcp

    def get(self, request, *args, **kwargs):
        return self.mcp_server.handle_django_request(request)

    def post(self, request, *args, **kwargs):
        return self.mcp_server.handle_django_request(request)
