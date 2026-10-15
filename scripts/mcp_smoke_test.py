#!/usr/bin/env python3
"""MCP Smoke Test Script for CampusMate AI.

Verifies end-to-end connectivity with the running FastMCP server:
1. Connects using the official MCP Python SDK (`streamablehttp_client` + `ClientSession`).
2. Transmits the Bearer authorization token.
3. Performs the MCP handshake (`initialize()`).
4. Discovers and lists all registered MCP tools.
5. Invokes the `daily_briefing` tool and prints the result.

Usage:
    python scripts/mcp_smoke_test.py
    MCP_SERVER_URL=http://localhost:8080/mcp MCP_AUTH_TOKEN=dev_mcp_secret_token_12345 python scripts/mcp_smoke_test.py
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.mcp_client import CampusMateMCPClient


def main():
    server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")
    auth_token = os.environ.get("MCP_AUTH_TOKEN", "dev_mcp_secret_token_12345")
    student_id = int(os.environ.get("MCP_STUDENT_ID", 1))

    print("=" * 60)
    print("CampusMate AI FastMCP Streamable-HTTP Smoke Test")
    print("=" * 60)
    print(f"Target URL : {server_url}")
    print(f"Auth Token : {'[Configured]' if auth_token else '[None]'}")
    print(f"Student ID : {student_id}")
    print("-" * 60)

    client = CampusMateMCPClient(server_url=server_url, auth_token=auth_token)

    try:
        print("[1/3] Connecting to FastMCP server & listing tools...")
        tools = client.list_tools()
        print(f"      Success! Found {len(tools)} registered tools:")
        for t in tools[:8]:
            print(f"      - {t['name']}: {t['description'][:60]}...")
        if len(tools) > 8:
            print(f"      ... and {len(tools) - 8} more tools.")

        print("\n[2/3] Calling 'daily_briefing' tool via Streamable-HTTP...")
        briefing = client.call_tool("daily_briefing", {"student_id": student_id})
        print(f"      Result received successfully!")
        print(f"      Output: \"{briefing}\"")

        print("\n[3/3] Calling 'get_dashboard' tool via Streamable-HTTP...")
        dash = client.call_tool("get_dashboard", {"student_id": student_id})
        print(f"      Result received successfully!")
        print(f"      Dashboard summary: {dash}")

        print("\n" + "=" * 60)
        print("MCP SMOKE TEST PASSED: Full Streamable-HTTP loop verified!")
        print("=" * 60)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] Smoke test encountered an error: {exc}", file=sys.stderr)
        print("\nTroubleshooting tips:", file=sys.stderr)
        print("1. Ensure MCP server is running: python start_mcp.py", file=sys.stderr)
        print("2. Check token match: MCP_AUTH_TOKEN must match start_mcp.py", file=sys.stderr)
        print("3. Check URL: streamable-http expects http://localhost:8080/mcp", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
