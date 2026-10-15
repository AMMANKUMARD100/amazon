"""Tests for the FastMCP Model Context Protocol (MCP) server tools.

Validates that wrapped tools and new tools (daily_briefing, calculate_cgpa, get_dashboard, get_timetable)
execute reliably and honor auth token verification.
"""

import os
import unittest
from backend.database.connection import execute_query, init_db
from backend.database.seed import seed_db
from backend.mcp_server import (
    TOOLS,
    validate_auth_token,
    daily_briefing,
    calculate_cgpa,
    get_dashboard,
    get_timetable,
    list_tasks,
    add_task,
    get_attendance_summary
)


class TestMCPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db()
        # Ensure we have student ID 1 with known attributes
        student = execute_query("SELECT id FROM students WHERE id = 1;", fetch_one=True)
        if not student:
            execute_query(
                "INSERT INTO students (id, full_name, matric_number, email, cgpa, current_semester) "
                "VALUES (1, 'Test Student', 'MAT001', 'test@campus.edu', 3.75, 4);",
                commit=True
            )

    def test_auth_token_validation(self):
        # Default behavior: when MCP_AUTH_TOKEN is unset and MCP_ALLOW_NO_AUTH is not true, rejects
        os.environ.pop("MCP_AUTH_TOKEN", None)
        os.environ.pop("MCP_ALLOW_NO_AUTH", None)
        self.assertFalse(validate_auth_token(None))
        self.assertFalse(validate_auth_token("Bearer some-token"))

        # When MCP_ALLOW_NO_AUTH=true, allow bypassing
        os.environ["MCP_ALLOW_NO_AUTH"] = "true"
        self.assertTrue(validate_auth_token(None))
        self.assertTrue(validate_auth_token("Bearer anything"))
        os.environ.pop("MCP_ALLOW_NO_AUTH", None)

        # When MCP_AUTH_TOKEN is set, enforces exact token match
        os.environ["MCP_AUTH_TOKEN"] = "dev_mcp_secret_token_12345"
        self.assertTrue(validate_auth_token("dev_mcp_secret_token_12345"))
        self.assertTrue(validate_auth_token("Bearer dev_mcp_secret_token_12345"))
        self.assertFalse(validate_auth_token("Bearer wrong-key"))
        self.assertFalse(validate_auth_token(""))
        self.assertFalse(validate_auth_token(None))
        os.environ.pop("MCP_AUTH_TOKEN", None)

    def test_mcp_http_middleware_authentication(self):
        from starlette.testclient import TestClient
        from backend.mcp_server import mcp_app

        os.environ["MCP_AUTH_TOKEN"] = "dev_mcp_secret_token_12345"
        starlette_app = mcp_app.streamable_http_app()
        client = TestClient(starlette_app, raise_server_exceptions=False)

        # 1. No token -> 401
        res_no_token = client.post("/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        self.assertEqual(res_no_token.status_code, 401)
        self.assertIn("Unauthorized", res_no_token.text)

        # 2. Wrong token -> 401
        res_wrong = client.post(
            "/mcp",
            headers={"Authorization": "Bearer wrong-token"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        self.assertEqual(res_wrong.status_code, 401)

        # 3. Correct token -> Passed through middleware (not 401)
        res_ok = client.post(
            "/mcp",
            headers={"Authorization": "Bearer dev_mcp_secret_token_12345"},
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        self.assertNotEqual(res_ok.status_code, 401)

        os.environ.pop("MCP_AUTH_TOKEN", None)

    def test_bound_student_id_enforcement(self):
        # When MCP_STUDENT_ID is not set, any valid int student_id is accepted
        os.environ.pop("MCP_STUDENT_ID", None)
        dash = get_dashboard(student_id=1)
        self.assertIsInstance(dash, dict)

        # When MCP_STUDENT_ID is set to 1, student_id=1 succeeds
        os.environ["MCP_STUDENT_ID"] = "1"
        dash_bound = get_dashboard(student_id=1)
        self.assertIsInstance(dash_bound, dict)

        # Mismatched student_id (e.g. 2 != 1) must be rejected
        with self.assertRaises(PermissionError):
            get_dashboard(student_id=2)

        os.environ.pop("MCP_STUDENT_ID", None)


    def test_tools_dictionary_coverage(self):
        self.assertIn("daily_briefing", TOOLS)
        self.assertIn("calculate_cgpa", TOOLS)
        self.assertIn("get_dashboard", TOOLS)
        self.assertIn("get_timetable", TOOLS)
        self.assertIn("list_tasks", TOOLS)
        self.assertIn("add_task", TOOLS)
        self.assertIn("get_attendance_summary", TOOLS)
        self.assertGreaterEqual(len(TOOLS), 17)

    def test_daily_briefing_tool(self):
        briefing = daily_briefing(student_id=1)
        self.assertIsInstance(briefing, str)
        self.assertIn("briefing", briefing.lower())
        self.assertIn("classes", briefing.lower())

    def test_get_dashboard_tool(self):
        dash = get_dashboard(student_id=1)
        self.assertIsInstance(dash, dict)
        self.assertIn("student_name", dash)
        self.assertIn("cgpa", dash)

    def test_get_timetable_tool(self):
        tt = get_timetable(student_id=1)
        self.assertIsInstance(tt, list)

    def test_calculate_cgpa_tool(self):
        res = calculate_cgpa(student_id=1)
        self.assertIsInstance(res, dict)
        self.assertIn("current_cgpa", res)
        self.assertIn("projected_cgpa", res)

    def test_list_and_add_task_mcp_wrapper(self):
        tasks_before = list_tasks(student_id=1, status="Pending")
        self.assertIsInstance(tasks_before, list)

        new_t = add_task(
            student_id=1,
            title="MCP Test Task",
            due_date="2026-11-20",
            priority="High",
            description="Created via FastMCP tool",
            subject_code="CS101"
        )
        self.assertIsInstance(new_t, dict)
        self.assertEqual(new_t["title"], "MCP Test Task")

    def test_get_attendance_summary_tool(self):
        att = get_attendance_summary(student_id=1)
        self.assertIsInstance(att, list)


if __name__ == "__main__":
    unittest.main()
