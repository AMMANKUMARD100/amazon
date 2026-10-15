#!/usr/bin/env python3
"""Start script for the CampusMate AI MCP Server.

Runs the FastMCP server on streamable-http transport alongside
the existing Flask REST API (which runs separately on port 5000).

Usage:
    python start_mcp.py                       # default port 8080
    MCP_PORT=9090 python start_mcp.py         # custom port
    MCP_AUTH_TOKEN=mytoken python start_mcp.py # with auth
"""

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from backend.mcp_server import mcp_app

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", 8080))
    print(f"Starting CampusMate AI MCP Server on port {port}...")
    print(f"Transport: streamable-http")
    print(f"Auth: {'enabled' if os.environ.get('MCP_AUTH_TOKEN') else 'disabled (dev mode)'}")
    print(f"Test with: python -m mcp inspector http://localhost:{port}/mcp")
    mcp_app.run(transport="streamable-http", host="0.0.0.0", port=port)
