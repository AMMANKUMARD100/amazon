import unittest
import os
import shutil
import tempfile
import json
from backend.config import Config

# Per-file isolated test database
temp_dir = tempfile.mkdtemp()
Config.DATABASE_PATH = os.path.join(temp_dir, "test_chat.db")

from backend.app import create_app
from backend.database.connection import init_db, execute_query
from backend.services.chat_service import (
    create_or_get_session,
    list_sessions,
    get_session_messages,
    append_message,
    delete_session
)
from backend.services.exceptions import ValidationError, NotFoundError


class TestChatHistoryAndMultiTurn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Seed student B for multi-tenant isolation tests if not already present
        existing_u = execute_query("SELECT id FROM users WHERE username = 'student_chat_b';", fetch_one=True)
        if not existing_u:
            u2 = execute_query(
                "INSERT INTO users (username, password_hash, role) VALUES ('student_chat_b', 'hash', 'Student');",
                commit=True
            )
            execute_query(
                "INSERT INTO students (user_id, email, matric_number, full_name, cgpa) VALUES (?, 'student_b@campus.edu', 'MAT_CHAT_B', 'Student Chat B', 3.7);",
                (u2,),
                commit=True
            )
        cls.student_b_id = execute_query("SELECT s.id FROM students s JOIN users u ON s.user_id = u.id WHERE u.username = 'student_chat_b';", fetch_one=True)[0]


    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(temp_dir, ignore_errors=True)

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # Log in student A (id 1)
        self.client.post('/api/auth/login', json={"username": "student", "password": "password123"})

    def test_session_creation_and_listing(self):
        sess = create_or_get_session(student_id=1, title="Test Chat 1")
        self.assertIsNotNone(sess.get("id"))
        self.assertEqual(sess["student_id"], 1)
        self.assertEqual(sess["title"], "Test Chat 1")

        sessions = list_sessions(student_id=1)
        self.assertGreaterEqual(len(sessions), 1)
        self.assertTrue(any(s["id"] == sess["id"] for s in sessions))

    def test_multi_turn_message_appending_and_audit_trace(self):
        sess = create_or_get_session(student_id=1, title="Audit Trace Session")
        sid = sess["id"]

        # Append user turn
        msg_user = append_message(student_id=1, session_id=sid, role="user", content="Show my pending tasks")
        self.assertEqual(msg_user["role"], "user")

        # Append assistant turn with audit trace
        mock_trace = [{
            "tool_name": "list_tasks",
            "input": {"status": "Pending"},
            "output": {"success": True, "result": []}
        }]
        msg_ast = append_message(
            student_id=1,
            session_id=sid,
            role="assistant",
            content="You have no pending tasks right now.",
            action_executed="list_tasks",
            tool_trace=mock_trace
        )
        self.assertEqual(msg_ast["action_executed"], "list_tasks")
        self.assertEqual(msg_ast["tool_trace"], mock_trace)

        # Retrieve messages
        history = get_session_messages(student_id=1, session_id=sid)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Show my pending tasks")
        self.assertEqual(history[1]["tool_trace"], mock_trace)

    def test_student_isolation_on_chat_history(self):
        # Create session for student 1
        sess_a = create_or_get_session(student_id=1, title="Student A Secret")
        append_message(student_id=1, session_id=sess_a["id"], role="user", content="Secret message")

        # Student B cannot read Student 1's messages
        with self.assertRaises(NotFoundError):
            get_session_messages(student_id=self.student_b_id, session_id=sess_a["id"])

        # Student B cannot append messages to Student 1's session
        with self.assertRaises(NotFoundError):
            append_message(student_id=self.student_b_id, session_id=sess_a["id"], role="user", content="Intruder")

        # Student B cannot delete Student 1's session
        with self.assertRaises(NotFoundError):
            delete_session(student_id=self.student_b_id, session_id=sess_a["id"])

    def test_chat_api_endpoints_authenticated(self):
        # 1. POST /api/chat/sessions
        res = self.client.post('/api/chat/sessions', json={"title": "API Created Session"})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        sid = data["session"]["id"]

        # 2. GET /api/chat/sessions
        list_res = self.client.get('/api/chat/sessions')
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(s["id"] == sid for s in list_res.get_json()["sessions"]))

        # 3. Simulate turn with session_id to verify automatic persistence
        sim_res = self.client.post('/api/alexa/simulate', json={
            "session_id": sid,
            "utterance": "What classes do I have today?"
        })
        self.assertEqual(sim_res.status_code, 200)

        # 4. GET /api/chat/sessions/<id>/messages
        msg_res = self.client.get(f'/api/chat/sessions/{sid}/messages')
        self.assertEqual(msg_res.status_code, 200)
        msgs = msg_res.get_json()["messages"]
        self.assertGreaterEqual(len(msgs), 2)  # 1 user + 1 assistant
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["role"], "assistant")
        self.assertIsNotNone(msgs[1].get("action_executed"))

        # 5. DELETE /api/chat/sessions/<id>
        del_res = self.client.delete(f'/api/chat/sessions/{sid}')
        self.assertEqual(del_res.status_code, 200)

    def test_unauthenticated_chat_endpoints_return_401(self):
        anon_client = self.app.test_client()
        res1 = anon_client.get('/api/chat/sessions')
        self.assertEqual(res1.status_code, 401)

        res2 = anon_client.post('/api/chat/sessions', json={"title": "Hack"})
        self.assertEqual(res2.status_code, 401)


if __name__ == '__main__':
    unittest.main()
