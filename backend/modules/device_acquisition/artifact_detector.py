# backend/modules/device_acquisition/artifact_detector.py

import os
import json
import csv
import sqlite3
import xml.etree.ElementTree as ET
from typing import Tuple
from modules.device_acquisition.supported_formats import FILENAME_TO_ARTIFACT_TYPE

class ArtifactDetector:
    @staticmethod
    def detect_sqlite_type(file_path: str) -> str:
        """Inspect SQLite schema/tables to identify the evidence type."""
        conn = None
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0].lower() for row in cursor.fetchall()]
            
            # Match schema tables
            if any(t in tables for t in ["contacts", "contact_methods", "raw_contacts", "phone_lookup"]):
                return "Contact"
            if any(t in tables for t in ["sms", "messages", "threads", "parts"]):
                return "SMS"
            if any(t in tables for t in ["calls", "call_log", "calllogs"]):
                return "Call"
            if any(t in tables for t in ["history", "urls", "visits", "bookmarks", "history_visits"]):
                return "BrowserHistory"
            if any(t in tables for t in ["location", "gps", "waypoints", "coordinates"]):
                return "GPS"
            if any(t in tables for t in ["applications", "apps", "packages"]):
                return "Application"
            return "SQLiteDatabase"
        except Exception:
            return "SQLiteDatabase"
        finally:
            if conn:
                conn.close()

    @staticmethod
    def detect_json_type(file_path: str) -> str:
        """Inspect JSON structure to identify evidence type."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            
            # If it's a list, look at the first record
            record = data[0] if isinstance(data, list) and len(data) > 0 else data
            if not isinstance(record, dict):
                return "JSON"
                
            keys = [k.lower() for k in record.keys()]
            
            # Heuristics based on keys
            if any(k in keys for k in ["phone", "phonenumber", "mobile", "first_name", "last_name"]):
                return "Contact"
            if any(k in keys for k in ["body", "message", "sms_body", "sender", "recipient"]):
                return "SMS"
            if any(k in keys for k in ["duration", "call_type", "phone_number", "caller"]):
                return "Call"
            if any(k in keys for k in ["url", "browser", "visit_count", "history"]):
                return "BrowserHistory"
            if any(k in keys for k in ["latitude", "longitude", "lat", "lon", "gps"]):
                return "GPS"
            if any(k in keys for k in ["app_name", "package", "bundle_id"]):
                return "Application"
            if any(k in keys for k in ["ssid", "bssid", "wifi"]):
                return "WiFi"
            if any(k in keys for k in ["mac_address", "bluetooth"]):
                return "Bluetooth"
            if any(k in keys for k in ["notification", "package_name", "ticker"]):
                return "Notification"
            if any(k in keys for k in ["device_name", "os_version", "serial_number", "imei"]):
                return "DeviceInformation"
            if any(k in keys for k in ["event_type", "confidence", "description"]):
                return "TimelineEvent"
            return "JSON"
        except Exception:
            return "JSON"

    @staticmethod
    def detect_xml_type(file_path: str) -> str:
        """Inspect XML root tag to identify evidence type."""
        try:
            parser = ET.iterparse(file_path, events=("start",))
            _, elem = next(parser)
            tag = elem.tag.lower()
            
            if "contact" in tag:
                return "Contact"
            if "sms" in tag or "message" in tag:
                return "SMS"
            if "call" in tag:
                return "Call"
            if "gps" in tag or "gpx" in tag or "trk" in tag or "wpt" in tag:
                return "GPS"
            if "app" in tag or "package" in tag:
                return "Application"
            return "XML"
        except Exception:
            return "XML"

    @staticmethod
    def detect_csv_type(file_path: str) -> str:
        """Inspect CSV header to identify evidence type."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader)
            
            cols = [c.lower().strip() for c in header]
            if any(c in cols for c in ["phone", "phonenumber", "mobile", "first_name", "last_name", "email"]):
                return "Contact"
            if any(c in cols for c in ["body", "message", "sender", "recipient", "sms_body"]):
                return "SMS"
            if any(c in cols for c in ["duration", "call_type", "phone_number", "caller"]):
                return "Call"
            if any(c in cols for c in ["url", "browser", "visit_count"]):
                return "BrowserHistory"
            if any(c in cols for c in ["latitude", "longitude", "lat", "lon", "gps"]):
                return "GPS"
            if any(c in cols for c in ["app_name", "package", "bundle_id"]):
                return "Application"
            return "CSV"
        except Exception:
            return "CSV"

    @staticmethod
    def detect(file_path: str) -> Tuple[str, str]:
        """Detect the MIME type/format and specific artifact type for a file.
        Returns:
            Tuple[detected_format, artifact_type]
            e.g. ("SQLite", "Call") or ("JPEG", "File")
        """
        # Read magic bytes to determine format
        header = b""
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
        except Exception:
            pass

        ext = os.path.splitext(file_path)[1].lower()
        
        # Format detection using magic bytes
        fmt = "Unknown"
        if header.startswith(b"SQLite format 3\x00"):
            fmt = "SQLite"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            fmt = "PNG"
        elif header.startswith(b"\xff\xd8\xff"):
            fmt = "JPEG"
        elif header.startswith(b"%PDF-"):
            fmt = "PDF"
        elif header.startswith(b"PK\x03\x04"):
            fmt = "ZIP"
        elif header.startswith(b"\x1f\x8b"):
            fmt = "GZIP"
        elif header.startswith(b"{\n") or header.startswith(b"[\n") or header.startswith(b"{") or header.startswith(b"["):
            fmt = "JSON"
        elif header.startswith(b"<?xml") or header.startswith(b"<"):
            fmt = "XML"
        else:
            # Try to infer by extension as fallback
            if ext in [".json"]: fmt = "JSON"
            elif ext in [".xml", ".gpx"]: fmt = "XML"
            elif ext in [".csv"]: fmt = "CSV"
            elif ext in [".txt"]: fmt = "TXT"
            elif ext in [".log"]: fmt = "LOG"
            elif ext in [".html", ".htm"]: fmt = "HTML"
            elif ext in [".mp4"]: fmt = "MP4"
            elif ext in [".avi"]: fmt = "AVI"
            elif ext in [".mov"]: fmt = "MOV"
            elif ext in [".mp3"]: fmt = "MP3"
            elif ext in [".wav"]: fmt = "WAV"
            elif ext in [".aac"]: fmt = "AAC"
            elif ext in [".tar"]: fmt = "TAR"
            elif ext in [".heic"]: fmt = "HEIC"
            
        # Now detect specific artifact types
        artifact_type = "File"
        
        if fmt == "SQLite":
            artifact_type = ArtifactDetector.detect_sqlite_type(file_path)
        elif fmt == "JSON":
            artifact_type = ArtifactDetector.detect_json_type(file_path)
        elif fmt == "XML":
            artifact_type = ArtifactDetector.detect_xml_type(file_path)
        elif fmt == "CSV":
            artifact_type = ArtifactDetector.detect_csv_type(file_path)
        elif fmt in ["JPEG", "PNG", "HEIC", "MP4", "AVI", "MOV", "MP3", "WAV", "AAC"]:
            artifact_type = "File"
        elif fmt in ["TXT", "LOG"]:
            name_lower = os.path.basename(file_path).lower()
            import re
            words = re.split(r'[^a-zA-Z0-9]', name_lower)
            matched = False
            for term, type_val in FILENAME_TO_ARTIFACT_TYPE.items():
                if term in words:
                    artifact_type = type_val
                    matched = True
                    break
            if not matched:
                artifact_type = "SystemLogs" if fmt == "LOG" else "File"
        else:
            name_lower = os.path.basename(file_path).lower()
            import re
            words = re.split(r'[^a-zA-Z0-9]', name_lower)
            for term, type_val in FILENAME_TO_ARTIFACT_TYPE.items():
                if term in words:
                    artifact_type = type_val
                    break
                    
        return fmt, artifact_type
