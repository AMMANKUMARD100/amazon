import os
import unittest
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
Config.DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_mcp.db')

from backend.app import create_app
from backend.database.connection import execute_query

class MCPTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
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

    def test_get_assignments(self):
        """Verifies getAssignments returns all seeded items."""
        # Query for student 1 (Alex Mercer)
        res = self.client.post('/api/mcp/getAssignments', json={"student_id": 1})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]['code'], 'CS105')

    def test_add_and_delete_assignment(self):
        """Verifies assignment mutations work as expected."""
        # Create
        res = self.client.post('/api/mcp/addAssignment', json={
            "student_id": 1,
            "subject_id": 1,
            "title": "Unit Test Assignment",
            "due_date": "2026-07-15",
            "priority": "High"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        assign_id = data["id"]
        
        # Verify exists
        check = execute_query("SELECT id FROM assignments WHERE id = ?;", (assign_id,), fetch_one=True)
        self.assertIsNotNone(check)
        
        # Delete
        del_res = self.client.delete('/api/mcp/deleteAssignment', json={"assignment_id": assign_id})
        self.assertEqual(del_res.status_code, 200)
        
        # Verify removed
        check = execute_query("SELECT id FROM assignments WHERE id = ?;", (assign_id,), fetch_one=True)
        self.assertIsNone(check)

    def test_calculate_attendance(self):
        """Verifies mathematical attendance values and heuristic outputs."""
        res = self.client.post('/api/mcp/calculateAttendance', json={"student_id": 1})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        # Find subject CS101: 9 Present, 1 Absent (90%)
        cs101 = next(item for item in data if item["code"] == "CS101")
        self.assertEqual(cs101["percentage"], 90.0)
        self.assertEqual(cs101["status"], "Good")
        self.assertEqual(cs101["classes_can_miss"], 2) # (9 - 3)/3 = 2
        
        # Find subject CS105: 5 Present, 5 Absent (50%)
        cs105 = next(item for item in data if item["code"] == "CS105")
        self.assertEqual(cs105["percentage"], 50.0)
        self.assertEqual(cs105["status"], "Low")
        self.assertEqual(cs105["classes_needed_for_75"], 10) # 3*5 - 5 = 10

if __name__ == '__main__':
    unittest.main()
