#!/usr/bin/env python
"""
Run the FastMCP server in stdio mode
"""
from server import mcp


if __name__ == "__main__":

    mcp.run(transport="streamable-http")
