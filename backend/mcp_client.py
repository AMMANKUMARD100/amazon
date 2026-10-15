"""Model Context Protocol (MCP) Python Client for CampusMate AI.

Built on the official MCP Python SDK (`streamablehttp_client` + `ClientSession`).
Connects to the CampusMate FastMCP server over streamable-HTTP using Bearer token authentication,
discovers registered tools, and calls tools remotely.
"""

import os
import anyio
from typing import Any, Dict, List, Optional
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class CampusMateMCPClient:
    """Async & sync client for communicating with the streamable-http FastMCP server."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 30.0
    ):
        base_url = server_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")
        self.server_url = base_url.rstrip("/") if not base_url.endswith("/mcp") else base_url
        if not self.server_url.endswith("/mcp"):
            self.server_url = f"{self.server_url}/mcp"

        self.auth_token = auth_token or os.environ.get("MCP_AUTH_TOKEN", "dev_mcp_secret_token_12345")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def list_tools_async(self) -> List[Dict[str, Any]]:
        """Connects via streamablehttp_client, initializes the session, and lists available tools."""
        headers = self._get_headers()
        async with streamablehttp_client(self.server_url, headers=headers, timeout=self.timeout) as (
            read_stream,
            write_stream,
            get_session_id
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.list_tools()
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in response.tools
                ]

    async def call_tool_async(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Connects via streamablehttp_client, initializes the session, and invokes a tool."""
        headers = self._get_headers()
        async with streamablehttp_client(self.server_url, headers=headers, timeout=self.timeout) as (
            read_stream,
            write_stream,
            get_session_id
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                # Unwrap FastMCP content text if present
                if hasattr(result, "content") and result.content:
                    first = result.content[0]
                    if hasattr(first, "text"):
                        return first.text
                return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for list_tools_async."""
        return anyio.run(self.list_tools_async)

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Synchronous wrapper for call_tool_async."""
        return anyio.run(lambda: self.call_tool_async(name, arguments))


# Global client singleton
mcp_client = CampusMateMCPClient()
