import os
import unittest
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
Config.DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_agents.db')

from backend.app import create_app
from backend.agents.agent_manager import AgentManager

class AgentsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.manager = AgentManager(student_id=1)
        
        # Clear rate limit store to prevent inter-test blocking
        from backend.middleware.security import rate_limit_store
        rate_limit_store.clear()

    def tearDown(self):
        self.app_context.pop()
        if os.path.exists(Config.DATABASE_PATH):
            try:
                os.remove(Config.DATABASE_PATH)
            except OSError:
                pass

    def test_planner_agent(self):
        """Verifies PlannerAgent generates valid study slots and handles difficulty adjustments."""
        res = self.manager.execute_agent("PlannerAgent")
        self.assertNotIn("error", res)
        self.assertTrue(res["success"])
        self.assertGreater(res["weekly_slots_allocated"], 0)
        
        # Verify slots contain required keys
        slot = res["study_plan"][0]
        self.assertIn("code", slot)
        self.assertIn("date", slot)
        self.assertIn("topic", slot)

    def test_attendance_agent_advice(self):
        """Verifies AttendanceAgent produces advice templates for at-risk courses."""
        res = self.manager.execute_agent("AttendanceAgent")
        self.assertNotIn("error", res)
        self.assertGreater(res["total_subjects"], 0)
        self.assertGreater(res["at_risk_subjects"], 0) # CS104 and CS105 are <75%
        
        # Find CS105 detail advice
        cs105 = next(item for item in res["details"] if item["code"] == "CS105")
        self.assertIn("Warning: Attendance is below 75%", cs105["advice"])

    def test_faq_agent_fuzzy_matching(self):
        """Verifies FAQAgent resolves student questions using offline keyterms search."""
        # Query: library location
        res = self.manager.execute_agent("FAQAgent", {"query": "library location"})
        self.assertNotIn("error", res)
        self.assertIn("Central Library is located in Block C", res["answer"])
        
        # Query: advisor contact
        res2 = self.manager.execute_agent("FAQAgent", {"query": "advisor email"})
        self.assertIn("email advising@campus.edu", res2["answer"])

if __name__ == '__main__':
    unittest.main()
