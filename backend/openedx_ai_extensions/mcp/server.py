"""
MCP Server implementation using FastMCP for OpenEdx AI Extensions

This module provides a Model Context Protocol (MCP) server that exposes
tools and resources for AI assistants to interact with the OpenEdx system.
"""

import logging

from asgiref.sync import sync_to_async
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import StructuredLoggingMiddleware
from opaque_keys.edx.keys import UsageKey

from .djangomcp import DjangoMCP

logger = logging.getLogger(__name__)

# Configure authentication provider
mcp = DjangoMCP(
    name="openedx_server",
)
mcp.add_middleware(StructuredLoggingMiddleware())
mcp.add_middleware(ErrorHandlingMiddleware())


@mcp.tool()
async def get_unit_content(course_id: str, unit_id: str) -> dict:  # pylint: disable=unused-argument
    """Extract unit content from Open edX modulestore"""

    try:
        # pylint: disable=import-error,import-outside-toplevel
        from xmodule.modulestore.django import modulestore

        if not unit_id:
            return {"error": "Missing unitId in context"}

        unit_key = await sync_to_async(UsageKey.from_string)(unit_id)
        store = modulestore()
        unit = await sync_to_async(store.get_item)(unit_key)

        unit_info = {
            "unit_id": str(unit.location),
            "display_name": unit.display_name,
            "category": unit.category,
            "blocks": [],
        }

        if hasattr(unit, "children") and unit.children:
            for child_key in unit.children:
                try:
                    child = await sync_to_async(store.get_item)(child_key)
                    block_info = {
                        "block_id": str(child.location),
                        "display_name": child.display_name,
                        "category": child.category,
                    }

                    if child.category == "html":
                        block_info["content"] = getattr(child, "data", "")
                    elif child.category == "problem":
                        block_info["content"] = getattr(child, "data", "")

                    unit_info["blocks"].append(block_info)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"Could not load block {child_key}: {e}")

        return unit_info

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"TEST Error accessing content for unit_id {unit_id}: {e}")
        return {"error": f"Error accessing content: {str(e)}"}
