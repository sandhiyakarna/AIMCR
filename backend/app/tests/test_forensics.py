import os
import sys
import json
import datetime
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import Base
from app.models.all import Case, Evidence, ThreatIndicator
from app.services.threat_intel import ThreatIntelService
from app.services.anti_forensics import AntiForensicsService
from app.services.risk_scorer import ForensicComplexityService
from app.services.recommendations import ForensicRecommendationsService

class TestForensicEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an in-memory SQLite database for testing
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()
        
        # 1. Seed Threat Indicators
        self.ti_phone = ThreatIndicator(
            indicator_type="phone_number",
            value="+18005550199",
            threat_name="Phishing SMS Sender",
            severity="High",
            description="Known sender of phishing SMS."
        )
        self.ti_domain = ThreatIndicator(
            indicator_type="domain",
            value="secure-auth-bank.net",
            threat_name="Phishing Domain",
            severity="Critical",
            description="Credential harvesting domain."
        )
        self.db.add_all([self.ti_phone, self.ti_domain])
        self.db.commit()

        # 2. Create mock case
        self.case = Case(
            title="Test Forensics Case",
            description="Forensics tests case",
            status="Active",
            investigator_id="test-user-id"
        )
        self.db.add(self.case)
        self.db.commit()

    def tearDown(self):
        # Clear tables
        self.db.query(Evidence).delete()
        self.db.query(ThreatIndicator).delete()
        self.db.query(Case).delete()
        self.db.commit()
        self.db.close()

    def test_threat_intel_phone_match(self):
        ev = Evidence(
            case_id=self.case.id,
            artifact_type="SMS",
            source="test.xml",
            hash="test-hash-1",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "phone_number": "+18005550199",
                "message": "Click the link immediately"
            })
        )
        self.db.add(ev)
        self.db.commit()

        matched = ThreatIntelService.check_and_annotate_evidence(self.db, ev)
        self.assertTrue(matched)
        
        # Reload and check metadata
        self.db.refresh(ev)
        meta = json.loads(ev.metadata_json)
        self.assertIn("threat_intel_match", meta)
        self.assertEqual(meta["threat_intel_match"]["threat_name"], "Phishing SMS Sender")

    def test_threat_intel_domain_match_in_message(self):
        ev = Evidence(
            case_id=self.case.id,
            artifact_type="SMS",
            source="test.xml",
            hash="test-hash-2",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "phone_number": "+123456789",
                "message": "Go to http://secure-auth-bank.net/login and verify details."
            })
        )
        self.db.add(ev)
        self.db.commit()

        matched = ThreatIntelService.check_and_annotate_evidence(self.db, ev)
        self.assertTrue(matched)
        
        self.db.refresh(ev)
        meta = json.loads(ev.metadata_json)
        self.assertEqual(meta["threat_intel_match"]["threat_name"], "Phishing Domain")

    def test_extension_spoofing_detection(self):
        ev = Evidence(
            case_id=self.case.id,
            artifact_type="File",
            source="Downloads.db",
            hash="test-hash-3",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "filename": "invoice.png",
                "mime_type": "application/vnd.android.package-archive",
                "magic_bytes": "504B0304"
            })
        )
        self.db.add(ev)
        self.db.commit()

        alerts = AntiForensicsService.detect(self.db, self.case.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "Extension Spoofing")
        self.assertIn("Android application package", alerts[0]["description"])

    def test_time_stomping_detection(self):
        base_time = datetime.datetime.now(datetime.timezone.utc)
        ev = Evidence(
            case_id=self.case.id,
            artifact_type="File",
            source="FileSystem.db",
            hash="test-hash-4",
            timestamp=base_time,
            metadata_json=json.dumps({
                "filename": "evidence.xlsx",
                "created_time": base_time.isoformat(),
                "modified_time": "1970-01-01T00:00:00Z"
            })
        )
        self.db.add(ev)
        self.db.commit()

        alerts = AntiForensicsService.detect(self.db, self.case.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "Time-Stomping Detected")

    def test_forensic_complexity_calculation(self):
        # Add threat intel match
        ev1 = Evidence(
            case_id=self.case.id,
            artifact_type="SMS",
            source="sms.xml",
            hash="hash-12345678901234567890123456789012",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "phone_number": "+18005550199",
                "threat_intel_match": {
                    "threat_name": "Phishing SMS Sender",
                    "severity": "High"
                }
            })
        )
        # Add extension spoofing
        ev2 = Evidence(
            case_id=self.case.id,
            artifact_type="File",
            source="FileSystem.db",
            hash="hash-22345678901234567890123456789012",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "filename": "fake_doc.jpg",
                "mime_type": "application/vnd.android.package-archive",
                "magic_bytes": "504B0304"
            })
        )
        self.db.add_all([ev1, ev2])
        self.db.commit()

        complexity = ForensicComplexityService.calculate_complexity(self.db, self.case.id)
        self.assertGreater(complexity["score"], 0)
        self.assertEqual(complexity["threat_intel_matches"], 1)
        self.assertEqual(complexity["anti_forensics_alerts"], 1)

    def test_recommendations_generation(self):
        ev = Evidence(
            case_id=self.case.id,
            artifact_type="File",
            source="FileSystem.db",
            hash="hash-32345678901234567890123456789012",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json=json.dumps({
                "filename": "fake_doc.jpg",
                "mime_type": "application/vnd.android.package-archive",
                "magic_bytes": "504B0304"
            })
        )
        self.db.add(ev)
        self.db.commit()

        recs = ForensicRecommendationsService.generate_recommendations(self.db, self.case.id)
        self.assertGreater(len(recs["recommendations"]), 0)
        self.assertTrue(any("file header magic signature verification" in r["action"].lower() for r in recs["recommendations"]))

if __name__ == "__main__":
    unittest.main()
