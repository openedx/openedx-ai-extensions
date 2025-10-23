"""
MCP Server implementation using FastMCP for OpenEdx AI Extensions

This module provides a Model Context Protocol (MCP) server that exposes
tools and resources for AI assistants to interact with the OpenEdx system.
"""
import logging
from typing import Any
from mcp.server.fastmcp import FastMCP
from starlette.responses import PlainTextResponse
from starlette.requests import Request
import random

logger = logging.getLogger(__name__)

mcp = FastMCP("dice_server", port=9001)

@mcp.tool()
def roll_dice(n_dice: int) -> list[int]:
    """Roll `n_dice` 6-sided dice and return the results."""
    return [random.randint(1, 6) for _ in range(n_dice)]
