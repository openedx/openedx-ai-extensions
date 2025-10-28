"""
MCP Server implementation using FastMCP for OpenEdx AI Extensions

This module provides a Model Context Protocol (MCP) server that exposes
tools and resources for AI assistants to interact with the OpenEdx system.
"""

import logging
import random

from .djangomcp import DjangoMCP

logger = logging.getLogger(__name__)


# Configure authentication provider

mcp = DjangoMCP(name="dice_server")


@mcp.tool()
async def roll_dice(n_dice: int) -> list[int]:
    """Roll `n_dice` 6-sided dice and return the results."""

    return [random.randint(1, 6) for _ in range(n_dice)]
