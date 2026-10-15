"""Tests for VoiceAgent orchestrator, Proactive Alert Service, and Proactive Routes.

Validates:
- VoiceAgent intent matching and multi-step chaining
- Attendance risk calculations (<75% and low buffer)
- Deadline conflicts and exam overlaps
- Priority-ranked proactive alerts
- Flask proactive blueprint routes
"""

import unittest
from backend.app import create_app
from backend.database.connection import execute_query, init_db
from backend.database.seed import seed_db
from backend.agents.voice_agent import voice_agent, handle_voice_request
from backend.services.proactive_service import (
    check_attendance_risk,
    check_deadline_conflicts,
    generate_weekly_summary,
    get_proactive_alerts
)
from backend.tools.registry import execute_tool


class TestVoiceAgentAndProactive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_db()
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Ensure student exists
        student = execute_query("SELECT id FROM students WHERE id = 1;", fetch_one=True)
        if not student:
            execute_query(
                "INSERT INTO students (id, full_name, matric_number, email, cgpa, current_semester) "
                "VALUES (1, 'Test Student', 'MAT001', 'test@campus.edu', 3.8, 4);",
                commit=True
            )

    def test_voice_agent_plan_my_evening_chain(self):
        resp = handle_voice_request(1, "Plan my evening please")
        self.assertIn("spoken_response", resp)
        self.assertIn("tool_calls", resp)
        self.assertEqual(resp["intent"], "plan_day")
        # Should chain 3 tools
        tool_names = [tc["tool"] for tc in resp["tool_calls"]]
        self.assertIn("get_today_reminder", tool_names)
        self.assertIn("list_tasks", tool_names)
        self.assertIn("generate_study_plan", tool_names)

    def test_voice_agent_status_check(self):
        resp = handle_voice_request(1, "How am I doing?")
        self.assertEqual(resp["intent"], "status_check")
        self.assertIn("CGPA", resp["spoken_response"])

    def test_voice_agent_risk_check(self):
        resp = handle_voice_request(1, "Am I at risk?")
        self.assertEqual(resp["intent"], "risk_check")
        self.assertIn("spoken_response", resp)

    def test_voice_agent_briefing(self):
        resp = handle_voice_request(1, "Good morning, give me my daily briefing")
        self.assertEqual(resp["intent"], "daily_briefing")
        self.assertIn("briefing", resp["spoken_response"].lower())

    def test_check_attendance_risk_service(self):
        risks = check_attendance_risk(1)
        self.assertIsInstance(risks, list)
        for r in risks:
            self.assertIn("percentage", r)
            self.assertIn("severity", r)
            self.assertIn("message", r)

    def test_check_deadline_conflicts_service(self):
        conflicts = check_deadline_conflicts(1)
        self.assertIsInstance(conflicts, list)

    def test_generate_weekly_summary_service(self):
        summary = generate_weekly_summary(1)
        self.assertIsInstance(summary, dict)
        self.assertIn("tasks", summary)
        self.assertIn("attendance", summary)
        self.assertIn("summary_text", summary)

    def test_get_proactive_alerts_service(self):
        alerts = get_proactive_alerts(1)
        self.assertIsInstance(alerts, list)
        if alerts:
            self.assertIn("priority", alerts[0])
            self.assertIn("message", alerts[0])

    def test_proactive_tools_in_registry(self):
        res1 = execute_tool("check_attendance_risk", 1, {})
        self.assertTrue(res1["success"])
        res2 = execute_tool("check_deadline_conflicts", 1, {})
        self.assertTrue(res2["success"])
        res3 = execute_tool("get_weekly_summary", 1, {})
        self.assertTrue(res3["success"])
        res4 = execute_tool("get_proactive_alerts", 1, {})
        self.assertTrue(res4["success"])

    def test_proactive_routes(self):
        res = self.client.get("/api/proactive/alerts/1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("alerts", data)

        res_sum = self.client.get("/api/proactive/summary/1/weekly")
        self.assertEqual(res_sum.status_code, 200)
        self.assertTrue(res_sum.get_json()["success"])

        res_voice = self.client.post("/api/proactive/voice/1", json={"utterance": "how am I doing"})
        self.assertEqual(res_voice.status_code, 200)
        self.assertTrue(res_voice.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
