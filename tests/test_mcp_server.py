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
        # When unset, passes
        os.environ.pop("MCP_AUTH_TOKEN", None)
        self.assertTrue(validate_auth_token(None))
        self.assertTrue(validate_auth_token("Bearer anything"))

        # When set, enforces exact token match
        os.environ["MCP_AUTH_TOKEN"] = "super-secret-mcp-key"
        self.assertTrue(validate_auth_token("super-secret-mcp-key"))
        self.assertTrue(validate_auth_token("Bearer super-secret-mcp-key"))
        self.assertFalse(validate_auth_token("Bearer wrong-key"))
        self.assertFalse(validate_auth_token(""))
        self.assertFalse(validate_auth_token(None))
        os.environ.pop("MCP_AUTH_TOKEN", None)

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
            description="Created via FastMCP tool"
        )
        self.assertIsInstance(new_t, dict)
        self.assertEqual(new_t["title"], "MCP Test Task")

    def test_get_attendance_summary_tool(self):
        att = get_attendance_summary(student_id=1)
        self.assertIsInstance(att, list)


if __name__ == "__main__":
    unittest.main()
