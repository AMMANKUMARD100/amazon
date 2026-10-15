import unittest
import os
import sys
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.database.connection import execute_query
from backend.services.task_service import add_task, list_tasks
from backend.services.exam_service import add_exam, list_exams, set_study_preference, get_study_preferences
from backend.services.planner_service import generate_study_plan

class TestStage2DataModelAndPlanner(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.client.post('/api/auth/login', json={"username": "student", "password": "password123"})

    def test_general_task_leaves_subjects_table_unchanged(self):
        """Adding a general task (no subject) must NOT create 'General Studies' or insert rows into subjects."""
        # Count initial subjects for student 1
        initial_subs = execute_query("SELECT id, code, name FROM subjects WHERE student_id = 1;", fetch_all=True)
        initial_count = len(initial_subs)
        initial_codes = {s['code'] for s in initial_subs}

        # Add a task with no subject
        task = add_task(
            student_id=1,
            title="General Errand Task",
            due_date="2026-11-28",
            priority="Low"
        )
        self.assertIsNone(task["subject_id"])
        self.assertEqual(task["code"], "GEN")
        self.assertEqual(task["subject_name"], "General")

        # Verify subjects table is completely untouched
        after_subs = execute_query("SELECT id, code, name FROM subjects WHERE student_id = 1;", fetch_all=True)
        self.assertEqual(len(after_subs), initial_count)
        after_codes = {s['code'] for s in after_subs}
        self.assertEqual(initial_codes, after_codes)
        self.assertNotIn("GEN", after_codes)

    def test_exam_crud_and_isolation(self):
        """Verify exams endpoints: create, list, and cross-student isolation."""
        res = self.client.post('/api/exams/', json={
            "title": "Midterm Algorithms",
            "exam_date": "2026-11-18",
            "notes": "Covers Dynamic Programming",
            "code": "CS105"
        })
        self.assertEqual(res.status_code, 201)
        exam_id = res.get_json()["exam"]["id"]

        # Read back
        get_res = self.client.get(f'/api/exams/{exam_id}')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()["title"], "Midterm Algorithms")

        # Verify Student B cannot access student 1's exam
        client_b = self.app.test_client()
        client_b.post('/api/auth/login', json={"username": "student_b", "password": "password123"})
        get_b_res = client_b.get(f'/api/exams/{exam_id}')
        self.assertEqual(get_b_res.status_code, 404)

    def test_planner_needs_input_when_no_hours(self):
        """Planner returns needs_input if no study hours are available in preferences or request."""
        # Clear student preferences for student 1
        execute_query("DELETE FROM study_preferences WHERE student_id = 1;", commit=True)
        
        # When neither preferences nor daily_hours provided and user requests explicit hours specification
        res = generate_study_plan(student_id=1, preferences={"require_hours": True})
        self.assertFalse(res["success"])
        self.assertIn("needs_input", res)
        self.assertIn("available_hours", res["needs_input"])

    def test_planner_no_sessions_after_exam_date(self):
        """Planner must not schedule any session for a subject after its exam date."""
        # Add an exam for CS101 in 3 days
        today = datetime.date.today()
        exam_date = (today + datetime.timedelta(days=3)).strftime("%Y-%m-%d")

        # Set preferences with 3.0 hours daily
        plan_res = generate_study_plan(student_id=1, preferences={
            "daily_hours": 3.0,
            "exam_dates": {"CS101": exam_date}
        })
        self.assertTrue(plan_res["success"])
        plan = plan_res["study_plan"]
        self.assertGreater(len(plan), 0)

        # For every CS101 slot, date must be <= exam_date
        for slot in plan:
            if slot["code"] == "CS101":
                self.assertLessEqual(slot["date"], exam_date, f"Slot {slot['date']} was scheduled after exam {exam_date}!")

if __name__ == '__main__':
    unittest.main()
