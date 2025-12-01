"""
MCP Server implementation using FastMCP for OpenEdx AI Extensions

This module provides a Model Context Protocol (MCP) server that exposes
tools and resources for AI assistants to interact with the OpenEdx system.
"""

import logging
import random

from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import StructuredLoggingMiddleware

from .djangomcp import DjangoMCP

logger = logging.getLogger(__name__)

# Configure authentication provider
mcp = DjangoMCP(
    name="openedx_server",
)
mcp.add_middleware(StructuredLoggingMiddleware())
mcp.add_middleware(ErrorHandlingMiddleware())


@mcp.tool()
def roll_dice(n_dice: int) -> list[int]:
    """Roll `n_dice` 6-sided dice and return the results."""
    number = [random.randint(1, 6) for _ in range(n_dice)]
    logger.info(f"Rolled {n_dice} dice: {number}")
    return number
