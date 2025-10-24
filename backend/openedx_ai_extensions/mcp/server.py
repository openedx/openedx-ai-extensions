"""
MCP Server implementation using FastMCP for OpenEdx AI Extensions

This module provides a Model Context Protocol (MCP) server that exposes
tools and resources for AI assistants to interact with the OpenEdx system.
"""
import logging
from typing import Any
from fastmcp import FastMCP, Context
from starlette.responses import PlainTextResponse
from starlette.requests import Request
import random
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware

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

mcp = FastMCP(name="dice_server", port=9001, auth=auth)
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(ErrorHandlingMiddleware(
    include_traceback=True,
    transform_errors=True,
))


@mcp.tool()
def roll_dice(n_dice: int) -> list[int]:
    """Roll `n_dice` 6-sided dice and return the results."""
    return [random.randint(1, 6) for _ in range(n_dice)]
