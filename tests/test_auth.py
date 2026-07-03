import os
import unittest
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
# Override database path for testing to run in isolation
Config.DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_auth.db')

from backend.app import create_app
from backend.database.connection import init_db
from backend.database.seed import seed_db
from backend.auth.auth_manager import authenticate_user

class AuthTestCase(unittest.TestCase):
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
        # Clean up test database file
        if os.path.exists(Config.DATABASE_PATH):
            try:
                os.remove(Config.DATABASE_PATH)
            except OSError:
                pass

    def test_database_seeding(self):
        """Verifies database contains seeded credentials after setup."""
        # Authenticate seeded student
        user = authenticate_user("student", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "student")
        self.assertEqual(user.role, "Student")

        # Authenticate seeded admin
        admin = authenticate_user("admin", "adminpassword123")
        self.assertIsNotNone(admin)
        self.assertEqual(admin.username, "admin")
        self.assertEqual(admin.role, "Admin")

    def test_invalid_login(self):
        """Ensures bad credentials are rejected."""
        user = authenticate_user("student", "wrong_password")
        self.assertIsNone(user)

        user = authenticate_user("nonexistent", "password123")
        self.assertIsNone(user)

    def test_login_api_route(self):
        """Tests the auth endpoint responses."""
        # Success login
        res = self.client.post('/api/auth/login', json={
            "username": "student",
            "password": "password123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["user"]["username"] == "student")
        
        # Invalid payload
        res = self.client.post('/api/auth/login', json={
            "username": "student"
        })
        self.assertEqual(res.status_code, 400)
        
        # Incorrect credentials
        res = self.client.post('/api/auth/login', json={
            "username": "student",
            "password": "wrongpassword"
        })
        self.assertEqual(res.status_code, 401)

if __name__ == '__main__':
    unittest.main()
