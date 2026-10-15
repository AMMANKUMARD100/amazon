import unittest
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.database.connection import execute_query
from backend.services.exceptions import ValidationError, NotFoundError

class TestAuthAndDataIsolation(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Ensure we have a second student in the test database for cross-tenant tests
        user_b = execute_query("SELECT id FROM users WHERE username = 'student_b';", fetch_one=True)
        if not user_b:
            user_b_id = execute_query(
                "INSERT INTO users (username, password_hash, role) VALUES ('student_b', 'scrypt:32768:8:1$dummy$dummy', 'Student');",
                commit=True
            )
            # Create student record for user_b
            from werkzeug.security import generate_password_hash
            execute_query(
                "UPDATE users SET password_hash = ? WHERE id = ?;",
                (generate_password_hash("password123"), user_b_id),
                commit=True
            )
            self.student_b_id = execute_query(
                "INSERT INTO students (user_id, full_name, email, matric_number) VALUES (?, 'Student Beta', 'beta@campus.edu', 'MAT999');",
                (user_b_id,),
                commit=True
            )
        else:
            st = execute_query("SELECT id FROM students WHERE user_id = ?;", (user_b['id'],), fetch_one=True)
            self.student_b_id = st['id']

    def test_unauthenticated_requests_fail(self):
        """All task, mcp and alexa endpoints must return 401 when unauthenticated."""
        endpoints = [
            ('/api/tasks/', 'GET'),
            ('/api/tasks/', 'POST'),
            ('/api/mcp/getAssignments', 'POST'),
            ('/api/mcp/calculateAttendance', 'POST'),
            ('/api/alexa/simulate', 'POST')
        ]
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, json={})
            self.assertEqual(res.status_code, 401, f"Expected 401 for {method} {url}, got {res.status_code}")

    def test_cross_tenant_isolation(self):
        """Student A cannot read, edit, complete, or delete Student B's tasks."""
        # 1. Log in as Student B and create a task
        client_b = self.app.test_client()
        login_res_b = client_b.post('/api/auth/login', json={"username": "student_b", "password": "password123"})
        self.assertEqual(login_res_b.status_code, 200)

        create_res = client_b.post('/api/tasks/', json={
            "title": "Student B Confidential Homework",
            "due_date": "2026-11-25",
            "priority": "High"
        })
        self.assertEqual(create_res.status_code, 201)
        task_b_id = create_res.get_json()["task"]["id"]

        # 2. Log in as Student A (default user 'student')
        client_a = self.app.test_client()
        login_res_a = client_a.post('/api/auth/login', json={"username": "student", "password": "password123"})
        self.assertEqual(login_res_a.status_code, 200)

        # Student A attempts to read Student B's task => 404 (NotFoundError)
        get_res = client_a.get(f'/api/tasks/{task_b_id}')
        self.assertEqual(get_res.status_code, 404)

        # Student A attempts to edit Student B's task => 404
        edit_res = client_a.put(f'/api/tasks/{task_b_id}', json={"title": "Hacked Title"})
        self.assertEqual(edit_res.status_code, 404)

        # Student A attempts to complete Student B's task => 404
        comp_res = client_a.post(f'/api/tasks/{task_b_id}/complete')
        self.assertEqual(comp_res.status_code, 404)

        # Student A attempts to delete Student B's task => 404
        del_res = client_a.delete(f'/api/tasks/{task_b_id}')
        self.assertEqual(del_res.status_code, 404)

        # Verify task B is intact
        check = execute_query("SELECT title, status FROM assignments WHERE id = ?;", (task_b_id,), fetch_one=True)
        self.assertEqual(check["title"], "Student B Confidential Homework")
        self.assertEqual(check["status"], "Pending")

if __name__ == '__main__':
    unittest.main()
