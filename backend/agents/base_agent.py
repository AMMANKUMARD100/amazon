import os
import requests
from flask import current_app, has_app_context
from backend.config import Config
from backend.middleware.logger import error_logger

class BaseAgent:
    """Base Agent class providing safe access to MCP Tool REST endpoints."""
    def __init__(self, student_id=None):
        self.student_id = student_id
        # Base url for standalone HTTP requests (e.g., in CLI mode)
        self.mcp_base_url = f"http://localhost:{os.environ.get('PORT', '5000')}/api/mcp"

    def call_mcp_tool(self, tool_name, method='POST', payload=None):
        """Calls an MCP tool endpoint.
        Uses Flask's test_client if running in-context, else uses HTTP requests.
        """
        if payload is None:
            payload = {}
            
        # Ensure student_id is set in payload if not present
        if self.student_id and 'student_id' not in payload:
            payload['student_id'] = self.student_id

        # Case 1: Inside active Flask Application Context (Web Server requests)
        if has_app_context():
            try:
                client = current_app.test_client()
                endpoint = f"/api/mcp/{tool_name}"
                
                # Setup session context for test_client if needed or rely on payload
                if method == 'POST':
                    response = client.post(endpoint, json=payload)
                else:
                    response = client.get(endpoint, query_string=payload)
                    
                if response.status_code >= 400:
                    error_logger.error(f"MCP Tool {tool_name} returned error status {response.status_code}: {response.data}")
                    return None
                return response.get_json()
            except Exception as e:
                error_logger.error(f"Error calling MCP tool {tool_name} via test_client: {e}")
                return None
                
        # Case 2: Outside application context (CLI runtime mode)
        else:
            try:
                url = f"{self.mcp_base_url}/{tool_name}"
                if method == 'POST':
                    response = requests.post(url, json=payload, timeout=5)
                else:
                    response = requests.get(url, params=payload, timeout=5)
                    
                if response.status_code >= 400:
                    error_logger.error(f"MCP Tool {tool_name} HTTP request failed: {response.text}")
                    return None
                return response.json()
            except Exception as e:
                error_logger.error(f"Network error calling MCP tool {tool_name} via HTTP: {e}")
                return None
