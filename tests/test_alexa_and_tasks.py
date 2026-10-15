import unittest
import json
from backend.app import create_app
from backend.database.connection import execute_query

class TestAlexaAndTasks(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_task_crud_and_persistence(self):
        # 1. Add Task with valid date
        res = self.client.post('/api/tasks/', json={
            "title": "Unit Test Assignment 1",
            "due_date": "2026-11-20",
            "priority": "High",
            "student_id": 1
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("task", data)
        task_id = data["task"]["id"]
        
        # Verify persistence in DB
        row = execute_query("SELECT id, title, status FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Unit Test Assignment 1")
        self.assertEqual(row["status"], "Pending")

        # 2. Add Task with invalid date format (must fail)
        invalid_res = self.client.post('/api/tasks/', json={
            "title": "Bad Date Task",
            "due_date": "not-a-date",
            "student_id": 1
        })
        self.assertEqual(invalid_res.status_code, 400)

        # 3. Complete Task
        comp_res = self.client.post(f'/api/tasks/{task_id}/complete', json={"student_id": 1})
        self.assertEqual(comp_res.status_code, 200)
        row_comp = execute_query("SELECT status FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
        self.assertEqual(row_comp["status"], "Completed")

        # 4. Delete Task
        del_res = self.client.delete(f'/api/tasks/{task_id}', json={"student_id": 1})
        self.assertEqual(del_res.status_code, 200)
        row_del = execute_query("SELECT id FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
        self.assertIsNone(row_del)

    def test_alexa_simulation_deterministic_intents(self):
        # Utterance: List tasks
        res = self.client.post('/api/alexa/simulate', json={
            "utterance": "Alexa, show my pending tasks",
            "student_id": 1
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("response", data)
        self.assertIn("outputSpeech", data["response"])
        self.assertEqual(data["simulation"]["mode"], "deterministic_demo")

        # Utterance: Check attendance
        res_att = self.client.post('/api/alexa/simulate', json={
            "utterance": "Alexa, check my attendance",
            "student_id": 1
        })
        self.assertEqual(res_att.status_code, 200)
        self.assertIn("attendance", res_att.get_json()["response"]["outputSpeech"]["text"].lower())

    def test_planner_grounding_with_preferences(self):
        # Trigger planner with user exam dates and priorities
        from backend.agents.agent_manager import AgentManager
        manager = AgentManager(student_id=1)
        plan = manager.execute_agent("PlannerAgent", {
            "daily_hours": 4.0,
            "exam_dates": {"CS101": "2026-11-15"},
            "priorities": {"CS101": "High"}
        })
        self.assertTrue(plan.get("success"))
        self.assertGreater(plan.get("weekly_slots_allocated"), 0)
        # Verify no missing dates
        for slot in plan.get("study_plan", []):
            self.assertRegex(slot["date"], r"^\d{4}-\d{2}-\d{2}$")

if __name__ == '__main__':
    unittest.main()
