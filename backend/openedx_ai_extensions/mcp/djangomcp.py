import contextvars
import json
import logging
from importlib import import_module
from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse
from fastmcp import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.datastructures import Headers
from starlette.types import Receive, Scope, Send

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

django_request_ctx = contextvars.ContextVar("django_request")


async def _call_starlette_handler(
    django_request: HttpRequest, session_manager: StreamableHTTPSessionManager
):
    """
    Adapts a Django request into a Starlette request and calls session_manager.handle_request.

    Returns:
        A Django HttpResponse
    """
    django_request_ctx.set(django_request)
    body = json.dumps(django_request.data, cls=DjangoJSONEncoder).encode("utf-8")

    # Build ASGI scope
    scope: Scope = {
        "type": "http",
        "http_version": "1.1",
        "method": django_request.method,
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in django_request.headers.items()
            if key.lower() != "content-length"
        ]
        + [("Content-Length", str(len(body)).encode("latin-1"))],
        "path": django_request.path,
        "raw_path": django_request.get_full_path().encode("utf-8"),
        "query_string": django_request.META["QUERY_STRING"].encode("latin-1"),
        "scheme": "https" if django_request.is_secure() else "http",
        "client": (django_request.META.get("REMOTE_ADDR"), 0),
        "server": (django_request.get_host(), django_request.get_port()),
    }

    async def receive() -> Receive:
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    # Prepare to collect send events
    response_started = {}
    response_body = bytearray()

    async def send(message: Send):
        if message["type"] == "http.response.start":
            response_started["status"] = message["status"]
            response_started["headers"] = Headers(raw=message["headers"])
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    async with session_manager.run():
        # Call transport
        await session_manager.handle_request(scope, receive, send)

    # Build Django HttpResponse
    status = response_started.get("status", 500)
    headers = response_started.get("headers", {})

    response = HttpResponse(
        bytes(response_body),
        status=status,
    )
    for key, value in headers.items():
        response[key] = value

    return response


# Extracted/adapted from django-mcp-server by Omar BENHAMID (https://github.com/gts360/django-mcp-server)
# Copyright (c) 2025 Omar BENHAMID
# Licensed under the MIT License
class DjangoMCP(FastMCP):
    def __init__(self, **kwargs):
        # Prevent extra server settings as we do not use the embedded server
        super().__init__(**kwargs)

    @property
    def session_manager(self) -> StreamableHTTPSessionManager:
        return StreamableHTTPSessionManager(
            app=self._mcp_server,
            event_store=None,
            json_response=True,
            stateless=True
        )

    def handle_django_request(self, request):
        """
        Handle a Django request and return a response.
        This method is called by the Django view when a request is received.
        """

        result = async_to_sync(_call_starlette_handler)(request, self.session_manager)

        return result
