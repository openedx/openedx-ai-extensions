"""
MCP Server implementation using FastMCP for OpenEdx AI Extensions

This module provides a Model Context Protocol (MCP) server that exposes
tools and resources for AI assistants to interact with the OpenEdx system.
"""

import logging
import random
import requests

from datetime import datetime
from typing import Any

from fastmcp import FastMCP, Context
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
from fastmcp.server.dependencies import AccessToken, get_access_token
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logger = logging.getLogger(__name__)

# Read public key for token validation
with open("public.pem", "r") as public_key_file:
    public_key_content = public_key_file.read()

# Configure authentication provider
auth = BearerAuthProvider(
    public_key=public_key_content,
    issuer="https://<your_ngrok_subdomain>.ngrok-free.app",
    audience="dice_server"
)

mcp = FastMCP(name="dice_server", port=9001)
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(
    ErrorHandlingMiddleware(
        include_traceback=True,
        transform_errors=True,
    )
)


@mcp.tool()
def roll_dice(n_dice: int) -> list[int]:
    """Roll `n_dice` 6-sided dice and return the results."""
    roll = [random.randint(1, 6) for _ in range(n_dice)]
    print(f"{datetime.now()}: roll {roll}")
    return roll


@mcp.tool()
def openedx_get_unit_content(location_id: str) -> dict:
    """Find the context of a `location_id` in a course in openedx"""

    print("[START] openedx_get_unit_content")
    headers = {
        # "Authorization": "Bearer your-jwt-token-here",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "http://local.openedx.io:8000/openedx-ai-extensions/v1/processors/openedxprocessor",
        json={
            "function": "get_unit_content",
            "context": {"extra_context": {"unitId": location_id}},
        },
        headers=headers,
    )
    print(f"[response] code{response.status_code}|")
    print(f"[response] text{response.text[:70]}|")

    # Check if request was successful
    if response.status_code != 200:
        return {
            "error": f"API request failed with status {response.status_code}",
            "details": response.text
        }

    # Parse JSON response
    result = response.json()

    print(
        f"{datetime.now()}: openedx_get_unit_content[{location_id}] -> {result.get('result', {}).get('display_name', 'N/A')}"
    )

    print("[FINISHED] openedx_get_unit_content")
    return result
