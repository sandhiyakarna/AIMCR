# backend/app/tests/test_acquisition.py

import os
import sys
import unittest
import tempfile
import json
import sqlite3
import datetime

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.device_acquisition.artifact_detector import ArtifactDetector
from modules.device_acquisition.parser_router import ParserRouter
from modules.device_acquisition.integrity_service import IntegrityService
from modules.device_acquisition.metadata_extractor import MetadataExtractor

class TestEvidenceAcquisition(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # clean up files
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_csv_contacts_parsing(self):
        path = os.path.join(self.temp_dir, "contacts.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("first_name,last_name,phone,email\nAlice,Smith,+15550011,alice@example.com\n")
        
        fmt, art_type, records = ParserRouter.route_and_parse(path)
        self.assertEqual(fmt, "CSV")
        self.assertEqual(art_type, "Contact")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["metadata"]["name"], "Alice Smith")
        self.assertEqual(records[0]["metadata"]["phone"], "+15550011")

    def test_json_sms_parsing(self):
        path = os.path.join(self.temp_dir, "sms_backup.json")
        data = [
            {"sender": "+15550022", "recipient": "Me", "body": "Hello World", "timestamp": "2026-07-20T12:00:00"}
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        fmt, art_type, records = ParserRouter.route_and_parse(path)
        self.assertEqual(fmt, "JSON")
        self.assertEqual(art_type, "SMS")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["metadata"]["body"], "Hello World")

    def test_corrupted_png_validation(self):
        path = os.path.join(self.temp_dir, "fake_image.png")
        with open(path, "wb") as f:
            f.write(b"NOT_A_REAL_PNG_SIGNATURE_DATA")
            
        valid, msg = IntegrityService.validate_file(path, "PNG")
        self.assertFalse(valid)
        self.assertIn("signature mismatch", msg.lower())

    def test_media_metadata_extraction(self):
        path = os.path.join(self.temp_dir, "test_photo.jpg")
        header = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00"
            b"\xff\xc0\x00\x11\x08\x04\x38\x07\x80\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01" # height 1080 (0x0438), width 1920 (0x0780)
            b"\xff\xd9"
        )
        with open(path, "wb") as f:
            f.write(header)
            
        fmt, art_type, records = ParserRouter.route_and_parse(path)
        self.assertEqual(fmt, "JPEG")
        self.assertEqual(art_type, "File")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["metadata"]["resolution"], "1920x1080")
        self.assertEqual(records[0]["metadata"]["filesize"], len(header))

    def test_unsupported_format(self):
        path = os.path.join(self.temp_dir, "malicious_payload.exe")
        with open(path, "wb") as f:
            f.write(b"\x4d\x5a\x90\x00\x03\x00\x00\x00")
            
        fmt, art_type, records = ParserRouter.route_and_parse(path)
        self.assertEqual(art_type, "File")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["metadata"]["extension"], ".exe")

if __name__ == "__main__":
    unittest.main()
