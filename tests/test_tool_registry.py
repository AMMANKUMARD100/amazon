import unittest
import os
import shutil
import tempfile
from backend.config import Config

# Per-file isolated test database
temp_dir = tempfile.mkdtemp()
Config.DATABASE_PATH = os.path.join(temp_dir, "test_tools.db")

from backend.app import create_app
from backend.database.connection import init_db, execute_query
from backend.tools import tool_registry, execute_tool, create_confirmation_token, verify_confirmation_token


class TestToolRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(temp_dir, ignore_errors=True)

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_registered_tools_count_and_schema(self):
        tools = tool_registry.list_tools()
        self.assertEqual(len(tools), 13)
        names = {t["name"] for t in tools}
        expected = {
            "list_tasks", "add_task", "update_task", "complete_task", "delete_task",
            "add_exam", "list_exams", "set_study_hours", "generate_study_plan",
            "save_study_plan", "get_today_summary", "get_attendance_summary", "search_faq"
        }
        self.assertEqual(names, expected)

    def test_reject_unknown_tool_and_invalid_student(self):
        # Invalid student
        res1 = execute_tool("list_tasks", None, {})
        self.assertFalse(res1["success"])
        self.assertEqual(res1["error"]["code"], "InvalidStudent")

        # Unknown tool
        res2 = execute_tool("non_existent_tool", 1, {})
        self.assertFalse(res2["success"])
        self.assertEqual(res2["error"]["code"], "UnknownTool")

    def test_schema_validation_and_reject_extra_args(self):
        # Missing required parameter 'title'
        res = execute_tool("add_task", 1, {"due_date": "2026-11-20"})
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "ValidationError")

        # Extra disallowed argument (schema additionalProperties is False)
        res_extra = execute_tool("add_task", 1, {
            "title": "Legit Title",
            "due_date": "2026-11-20",
            "malicious_extra_field": "hack"
        })
        self.assertFalse(res_extra["success"])
        self.assertEqual(res_extra["error"]["code"], "ValidationError")

    def test_task_tools_lifecycle(self):
        # 1. Add Task
        add_res = execute_tool("add_task", 1, {
            "title": "Registry Homework",
            "due_date": "2026-11-15",
            "priority": "High"
        })
        self.assertTrue(add_res["success"])
        task_id = add_res["result"]["id"]
        self.assertEqual(add_res["result"]["title"], "Registry Homework")

        # 2. Update Task
        up_res = execute_tool("update_task", 1, {
            "task_id": task_id,
            "priority": "Low",
            "description": "Updated description"
        })
        self.assertTrue(up_res["success"])
        self.assertEqual(up_res["result"]["priority"], "Low")

        # 3. Complete Task
        comp_res = execute_tool("complete_task", 1, {"task_id": task_id})
        self.assertTrue(comp_res["success"])
        self.assertEqual(comp_res["result"]["status"], "Completed")

        # 4. List Tasks
        list_res = execute_tool("list_tasks", 1, {"status": "Completed"})
        self.assertTrue(list_res["success"])
        self.assertTrue(any(t["id"] == task_id for t in list_res["result"]))

    def test_destructive_delete_requires_confirmation_token(self):
        # Create a task to delete
        t = execute_tool("add_task", 1, {"title": "Delete Me Task", "due_date": "2026-11-25"})
        task_id = t["result"]["id"]

        # Call delete_task without confirm_token -> returns pending_confirmation with token
        del_step1 = execute_tool("delete_task", 1, {"task_id": task_id})
        self.assertTrue(del_step1["success"])
        self.assertTrue(del_step1["result"].get("pending_confirmation"))
        token = del_step1["result"].get("confirm_token")
        self.assertIsNotNone(token)

        # Verify task is NOT deleted yet
        task_still_there = execute_query("SELECT id FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
        self.assertIsNotNone(task_still_there)

        # Confirm with wrong student -> fails
        wrong_stu = execute_tool("delete_task", 2, {"confirm_token": token})
        self.assertFalse(wrong_stu["success"])
        self.assertEqual(wrong_stu["error"]["code"], "ValidationError")

        # Confirm with correct student and token -> successfully deletes
        del_step2 = execute_tool("delete_task", 1, {"confirm_token": token})
        self.assertTrue(del_step2["success"])
        self.assertIn("deleted successfully", del_step2["result"]["message"])

        # Verify task is deleted from database
        deleted_task = execute_query("SELECT id FROM assignments WHERE id = ?;", (task_id,), fetch_one=True)
        self.assertIsNone(deleted_task)

        # Token cannot be re-used (single-use)
        del_step3 = execute_tool("delete_task", 1, {"confirm_token": token})
        self.assertFalse(del_step3["success"])
        self.assertEqual(del_step3["error"]["code"], "ValidationError")

    def test_ambiguity_handling_on_duplicate_names(self):
        # Create two tasks with similar names
        execute_tool("add_task", 1, {"title": "Physics Lab 1", "due_date": "2026-11-10"})
        execute_tool("add_task", 1, {"title": "Physics Lab 2", "due_date": "2026-11-12"})

        # Target "Physics Lab" by title -> returns ambiguity candidates instead of deleting/completing one arbitrarily
        res = execute_tool("complete_task", 1, {"task_title": "Physics Lab"})
        self.assertTrue(res["success"])
        self.assertTrue(res["result"].get("ambiguity"))
        candidates = res["result"].get("candidates", [])
        self.assertGreaterEqual(len(candidates), 2)

    def test_exam_and_study_hours_tools(self):
        # Add exam
        ex_res = execute_tool("add_exam", 1, {
            "title": "Midterm Exam",
            "exam_date": "2026-11-30",
            "subject_code": "CS101"
        })
        self.assertTrue(ex_res["success"])
        self.assertEqual(ex_res["result"]["title"], "Midterm Exam")

        # List exams
        list_ex = execute_tool("list_exams", 1, {})
        self.assertTrue(list_ex["success"])
        self.assertTrue(any(e["title"] == "Midterm Exam" for e in list_ex["result"]))

        # Set study hours (single day)
        hrs_res = execute_tool("set_study_hours", 1, {
            "weekday": "Monday",
            "available_hours": 3.5
        })
        self.assertTrue(hrs_res["success"])
        self.assertEqual(hrs_res["result"]["available_hours"], 3.5)

        # Set bulk study hours
        bulk_res = execute_tool("set_study_hours", 1, {
            "preferences": {"Tuesday": 4.0, "Wednesday": 2.5}
        })
        self.assertTrue(bulk_res["success"])
        self.assertEqual(bulk_res["result"]["Tuesday"], 4.0)

    def test_generate_and_save_study_plan_destructive_confirmation(self):
        # Generate plan
        plan_res = execute_tool("generate_study_plan", 1, {"daily_hours": 3.0})
        self.assertTrue(plan_res["success"])
        slots = plan_res["result"].get("study_plan", [])
        self.assertGreater(len(slots), 0)

        # Save study plan (first time, no existing sessions or initial)
        save_res = execute_tool("save_study_plan", 1, {"slots": slots[:2]})
        self.assertTrue(save_res["success"])

        # Second save when sessions already exist -> requires confirmation
        save_res2 = execute_tool("save_study_plan", 1, {"slots": slots[:1]})
        self.assertTrue(save_res2["success"])
        self.assertTrue(save_res2["result"].get("pending_confirmation"))
        token = save_res2["result"]["confirm_token"]

        # Confirm saving with token
        confirm_save = execute_tool("save_study_plan", 1, {"slots": slots[:1], "confirm_token": token})
        self.assertTrue(confirm_save["success"])
        self.assertIn("Successfully saved", confirm_save["result"]["message"])

    def test_information_tools(self):
        # Today summary
        today = execute_tool("get_today_summary", 1, {})
        self.assertTrue(today["success"])
        self.assertIn("classes", today["result"])

        # Attendance summary
        att = execute_tool("get_attendance_summary", 1, {})
        self.assertTrue(att["success"])
        self.assertIsInstance(att["result"], list)

        # Search FAQ
        faq = execute_tool("search_faq", 1, {"query": "wifi"})
        self.assertTrue(faq["success"])
        self.assertIsInstance(faq["result"], list)


if __name__ == '__main__':
    unittest.main()
