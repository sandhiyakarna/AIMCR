# backend/app/tests/test_ai_copilot.py

import os
import sys
import json
import datetime
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import Base, get_db
from app.models.all import Case, Evidence, User, TimelineEvent
from app.services.ollama_service import OllamaService
from app.services.copilot import CopilotService
from app.main import app

class TestAICopilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an in-memory SQLite database using StaticPool to share connection across threads
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        # Mock authentication dependency
        from app.api.deps import get_current_user
        
        cls.test_user_owner = User(
            id="user-owner-id",
            name="Alice Owner",
            email="alice@example.com",
            password_hash="fake-hash",
            role="Investigator"
        )
        cls.test_user_other = User(
            id="user-other-id",
            name="Bob Other",
            email="bob@example.com",
            password_hash="fake-hash",
            role="Investigator"
        )
        cls.current_test_user = cls.test_user_owner

        def mock_get_current_user():
            return cls.current_test_user

        app.dependency_overrides[get_current_user] = mock_get_current_user

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def setUp(self):
        self.db = self.SessionLocal()
        
        # Override get_db FastAPI dependency
        def mock_get_db():
            try:
                yield self.db
            finally:
                pass
        app.dependency_overrides[get_db] = mock_get_db

        # Add users first to satisfy foreign key constraints
        self.owner = User(
            id="user-owner-id",
            name="Alice Owner",
            email="alice@example.com",
            password_hash="fake-hash",
            role="Investigator"
        )
        self.other = User(
            id="user-other-id",
            name="Bob Other",
            email="bob@example.com",
            password_hash="fake-hash",
            role="Investigator"
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()

        # Create mock case
        self.case = Case(
            id="test-case-id",
            title="Test AI Copilot Case",
            description="Forensics tests case summary",
            status="Active",
            investigator_id="user-owner-id"
        )
        self.db.add(self.case)
        
        # Create mock evidence
        self.ev1 = Evidence(
            id="sms-ev-id",
            case_id="test-case-id",
            artifact_type="SMS",
            source="backup.xml",
            hash="sha256-hash-1",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "phone_number": "+18005550199",
                "message": "Verify account at http://secure-bank.net"
            })
        )
        self.ev2 = Evidence(
            id="gps-ev-id",
            case_id="test-case-id",
            artifact_type="GPS",
            source="location.db",
            hash="sha256-hash-2",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "latitude": 40.7128,
                "longitude": -74.0060
            })
        )
        self.db.add_all([self.ev1, self.ev2])
        
        # Create mock timeline event
        self.te1 = TimelineEvent(
            id="timeline-ev-1",
            case_id="test-case-id",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            event_type="SMS",
            description="Phishing SMS received",
            confidence=0.9,
            evidence_references=json.dumps(["sms-ev-id"])
        )
        self.db.add(self.te1)
        self.db.commit()

        self.client = TestClient(app)

    def tearDown(self):
        # Clear tables
        self.db.query(TimelineEvent).delete()
        self.db.query(Evidence).delete()
        self.db.query(Case).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()

    def test_ollama_service_is_available_returns_bool(self):
        is_avail = OllamaService.is_available(timeout=0.5)
        self.assertIsInstance(is_avail, bool)

    def test_copilot_rag_context_building(self):
        context = CopilotService.build_structured_context(self.db, "test-case-id", [self.ev1, self.ev2])
        self.assertIn("Test AI Copilot Case", context)
        self.assertIn("sms-ev-id", context)
        self.assertIn("gps-ev-id", context)
        self.assertIn("http://secure-bank.net", context)

    @patch("app.services.ollama_service.OllamaService.generate")
    def test_ai_query_api_success(self, mock_generate):
        # Mock LLM successful response
        mock_generate.return_value = {
            "success": True,
            "response": (
                "Based on the evidence, a phishing SMS was received. "
                "Citing evidence ID sms-ev-id.\n\n"
                "---STRUCTURED---\n"
                "{\n"
                "  \"confidence\": \"High\",\n"
                "  \"limitations\": [\"No browser logs found.\"]\n"
                "}\n"
                "---END---"
            ),
            "model": "qwen3:8b",
            "error": None
        }

        # Set user to owner
        TestAICopilot.current_test_user = self.test_user_owner
        
        response = self.client.post(
            "/api/copilot/investigations/test-case-id/ai/query",
            json={"question": "Analyze the suspicious activity"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("phishing SMS was received", data["answer"])
        self.assertNotIn("---STRUCTURED---", data["answer"])
        self.assertEqual(data["confidence"], "High")
        self.assertEqual(data["limitations"], ["No browser logs found."])
        self.assertEqual(data["evidence_references"], ["sms-ev-id"])
        self.assertEqual(data["timeline_references"], ["timeline-ev-1"])

    def test_ai_query_api_authorization_denied(self):
        # Set user to other investigator (Bob)
        TestAICopilot.current_test_user = self.test_user_other
        
        response = self.client.post(
            "/api/copilot/investigations/test-case-id/ai/query",
            json={"question": "Summarize suspicious activity"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Not authorized", response.json()["detail"])

    @patch("app.services.ollama_service.OllamaService.generate")
    def test_ai_query_api_ollama_unavailable_fallback(self, mock_generate):
        # Mock LLM service failure
        mock_generate.return_value = {
            "success": False,
            "response": "",
            "model": "qwen3:8b",
            "error": "Timeout"
        }

        # Set user to owner
        TestAICopilot.current_test_user = self.test_user_owner
        
        response = self.client.post(
            "/api/copilot/investigations/test-case-id/ai/query",
            json={"question": "Was there any phishing sms link?"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("AI investigation assistance is currently unavailable", data["answer"])
        self.assertIn("phishing", data["answer"].lower())
        self.assertEqual(data["confidence"], "Low (Local Fallback)")
        self.assertIn("timed out", data["limitations"][0])

    @patch("app.services.ollama_service.OllamaService.generate")
    def test_case_ai_summary_api(self, mock_generate):
        mock_generate.return_value = {
            "success": True,
            "response": (
                "Case Summary details...\n"
                "---STRUCTURED---\n"
                "{\n"
                "  \"confidence\": \"Medium\",\n"
                "  \"limitations\": []\n"
                "}\n"
                "---END---"
            ),
            "model": "qwen3:8b",
            "error": None
        }

        TestAICopilot.current_test_user = self.test_user_owner
        
        response = self.client.get("/api/copilot/investigations/test-case-id/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Case Summary details", data["summary"])
        self.assertEqual(data["confidence"], "Medium")

if __name__ == "__main__":
    unittest.main()
