import unittest
import json
import sys
import os

# --- THE FIX: Add the parent directory to the system path ---
# This tells Python: "Look one folder up from where this file is."
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ------------------------------------------------------------

from app import app

class BasicTests(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = app.test_client()
        # Propagate exceptions to the test client
        self.app.testing = True

    def test_health_check(self):
        """Test if the backend is running"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_create_overlay(self):
        """Test creating a new overlay"""
        # We need to mock the database or accept that this adds real data
        # For a simple assignment, adding data is fine, but cleaning it up is better.
        payload = {
            "content": "Unit Test Overlay", 
            "type": "text", 
            "x": 10, 
            "y": 10
        }
        response = self.app.post('/overlays', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        # Check if the response contains the data we sent
        data = json.loads(response.data)
        self.assertEqual(data['content'], "Unit Test Overlay")

if __name__ == "__main__":
    unittest.main()