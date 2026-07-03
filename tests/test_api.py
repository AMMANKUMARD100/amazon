import os
import unittest
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
Config.DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_api_sec.db')

from backend.app import create_app

class APITestCase(unittest.TestCase):
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

    def test_security_headers(self):
        """Verifies defensive HTTP headers are attached to responses."""
        res = self.client.get('/api/auth/status')
        self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(res.headers.get('X-Frame-Options'), 'DENY')
        self.assertIn('Content-Security-Policy', res.headers)

    def test_not_found_handling(self):
        """Verifies unrecognized paths return clean JSON structures with 404 status."""
        res = self.client.get('/api/invalid/path/route')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["error"], "NotFound")
        self.assertEqual(data["message"], "Requested resource not found.")

    def test_rate_limiting_login(self):
        """Verifies rate-limit middleware blocks spam login attempts."""
        # Make 11 rapid requests to login. Limit is 10 per minute.
        for i in range(11):
            res = self.client.post('/api/auth/login', json={
                "username": "student",
                "password": "wrongpassword"
            })
            if i < 10:
                self.assertEqual(res.status_code, 401)
            else:
                self.assertEqual(res.status_code, 429)
                data = res.get_json()
                self.assertEqual(data["error"], "RateLimitExceeded")

if __name__ == '__main__':
    unittest.main()
