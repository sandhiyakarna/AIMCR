# backend/modules/device_acquisition/parser_factory.py

import os
import csv
import json
import sqlite3
import datetime
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

from modules.device_acquisition.artifact_registry import BaseParser, ParserRegistry
from modules.device_acquisition.metadata_extractor import MetadataExtractor
from modules.device_acquisition.hash_service import HashService

# Helper to parse dates robustly
def parse_date(date_str: str) -> datetime.datetime:
    if not date_str:
        return datetime.datetime.utcnow()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    try:
        return datetime.datetime.fromisoformat(date_str)
    except Exception:
        return datetime.datetime.utcnow()

# --- 1. Contacts Parser ---
class ContactsParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "Contact"

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".json", ".xml", ".db", ".sqlite"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        # Check if contacts/contact is in path or matches name heuristic
        basename = os.path.basename(file_path).lower()
        return "contact" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".csv":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        records.append({
                            "timestamp": datetime.datetime.now(datetime.timezone.utc),
                            "metadata": {
                                "name": row.get("name", row.get("first_name", "")) + " " + row.get("last_name", ""),
                                "phone": row.get("phone", row.get("phone_number", row.get("mobile", ""))),
                                "email": row.get("email", ""),
                                "raw_data": row
                            }
                        })
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    records.append({
                        "timestamp": datetime.datetime.utcnow(),
                        "metadata": {
                            "name": item.get("name", item.get("first_name", "")) + " " + item.get("last_name", ""),
                            "phone": item.get("phone", item.get("phone_number", item.get("mobile", ""))),
                            "email": item.get("email", ""),
                            "raw_data": item
                        }
                    })
            elif ext in [".db", ".sqlite"]:
                conn = sqlite3.connect(file_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # Find contacts table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
                target_table = None
                for t in tables:
                    if "contact" in t.lower():
                        target_table = t
                        break
                if target_table:
                    cursor.execute(f"SELECT * FROM {target_table} LIMIT 500;")
                    for row in cursor.fetchall():
                        d = dict(row)
                        records.append({
                            "timestamp": datetime.datetime.utcnow(),
                            "metadata": {
                                "name": d.get("name", d.get("display_name", "")),
                                "phone": d.get("phone", d.get("phone_number", "")),
                                "email": d.get("email", ""),
                                "raw_data": d
                            }
                        })
                conn.close()
        except Exception:
            pass
        return records

# --- 2. SMS Parser ---
class SMSParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "SMS"

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".json", ".xml", ".db", ".sqlite"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        basename = os.path.basename(file_path).lower()
        return "sms" in basename or "message" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".csv":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        t = parse_date(row.get("timestamp", row.get("date", "")))
                        records.append({
                            "timestamp": t,
                            "metadata": {
                                "sender": row.get("sender", row.get("address", "")),
                                "recipient": row.get("recipient", row.get("to", "")),
                                "body": row.get("body", row.get("message", "")),
                                "direction": row.get("direction", "incoming"),
                                "raw_data": row
                            }
                        })
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = parse_date(item.get("timestamp", item.get("date", "")))
                    records.append({
                        "timestamp": t,
                        "metadata": {
                            "sender": item.get("sender", item.get("address", "")),
                            "recipient": item.get("recipient", item.get("to", "")),
                            "body": item.get("body", item.get("message", "")),
                            "direction": item.get("direction", "incoming"),
                            "raw_data": item
                        }
                    })
            elif ext in [".db", ".sqlite"]:
                conn = sqlite3.connect(file_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0].lower() for r in cursor.fetchall()]
                if "sms" in tables:
                    cursor.execute("SELECT * FROM sms LIMIT 500;")
                    for row in cursor.fetchall():
                        d = dict(row)
                        # SQLite dates are often millisecond timestamps
                        date_val = d.get("date", d.get("timestamp", ""))
                        try:
                            t = datetime.datetime.fromtimestamp(float(date_val)/1000.0)
                        except Exception:
                            t = datetime.datetime.utcnow()
                        records.append({
                            "timestamp": t,
                            "metadata": {
                                "sender": d.get("address", ""),
                                "recipient": d.get("recipient", "Me"),
                                "body": d.get("body", ""),
                                "direction": "incoming" if d.get("type", 1) == 1 else "outgoing",
                                "raw_data": d
                            }
                        })
                conn.close()
        except Exception:
            pass
        return records

# --- 3. Call Log Parser ---
class CallLogParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "Call"

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".json", ".xml", ".db", ".sqlite"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        basename = os.path.basename(file_path).lower()
        return "call" in basename or "calllog" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".csv":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        t = parse_date(row.get("timestamp", row.get("date", "")))
                        records.append({
                            "timestamp": t,
                            "metadata": {
                                "caller": row.get("caller", row.get("number", "")),
                                "duration": row.get("duration", "0"),
                                "call_type": row.get("type", row.get("call_type", "incoming")),
                                "raw_data": row
                            }
                        })
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = parse_date(item.get("timestamp", item.get("date", "")))
                    records.append({
                        "timestamp": t,
                        "metadata": {
                            "caller": item.get("caller", item.get("number", "")),
                            "duration": item.get("duration", "0"),
                            "call_type": item.get("type", item.get("call_type", "incoming")),
                            "raw_data": item
                        }
                    })
        except Exception:
            pass
        return records

# --- 4. Browser History Parser ---
class BrowserHistoryParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "BrowserHistory"

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".json", ".db", ".sqlite"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        basename = os.path.basename(file_path).lower()
        return "browser" in basename or "history" in basename or "chrome" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".csv":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        t = parse_date(row.get("timestamp", row.get("visit_time", "")))
                        records.append({
                            "timestamp": t,
                            "metadata": {
                                "url": row.get("url", ""),
                                "title": row.get("title", ""),
                                "visit_count": row.get("visit_count", "1"),
                                "raw_data": row
                            }
                        })
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = parse_date(item.get("timestamp", item.get("visit_time", "")))
                    records.append({
                        "timestamp": t,
                        "metadata": {
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "visit_count": item.get("visit_count", "1"),
                            "raw_data": item
                        }
                    })
        except Exception:
            pass
        return records

# --- 5. GPS Parser ---
class GPSParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "GPS"

    @property
    def supported_extensions(self) -> List[str]:
        return [".xml", ".gpx", ".json", ".csv"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        basename = os.path.basename(file_path).lower()
        return "gps" in basename or "location" in basename or "gpx" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in [".xml", ".gpx"]:
                tree = ET.parse(file_path)
                root = tree.getroot()
                # Simple GPX parsing namespaces
                namespaces = {'gpx': 'http://www.topografix.com/GPX/1/1'}
                # Try finding trackpoints or waypoints
                points = root.findall('.//gpx:trkpt', namespaces) or root.findall('.//trkpt') or root.findall('.//wpt')
                for pt in points:
                    lat = pt.attrib.get('lat', '0')
                    lon = pt.attrib.get('lon', '0')
                    time_elem = pt.find('time') or pt.find('.//time')
                    t_str = time_elem.text if time_elem is not None else ""
                    t = parse_date(t_str)
                    records.append({
                        "timestamp": t,
                        "metadata": {
                            "latitude": float(lat),
                            "longitude": float(lon),
                            "elevation": pt.find('ele').text if pt.find('ele') is not None else "0",
                            "name": pt.find('name').text if pt.find('name') is not None else "Waypoint"
                        }
                    })
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    t = parse_date(item.get("timestamp", item.get("time", "")))
                    records.append({
                        "timestamp": t,
                        "metadata": {
                            "latitude": float(item.get("latitude", item.get("lat", 0))),
                            "longitude": float(item.get("longitude", item.get("lon", 0))),
                            "accuracy": item.get("accuracy", "Unknown"),
                            "raw_data": item
                        }
                    })
        except Exception:
            pass
        return records

# --- 6. Installed Apps Parser ---
class InstalledAppsParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "Application"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json", ".csv"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        basename = os.path.basename(file_path).lower()
        return "app" in basename or "package" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                records.append({
                    "timestamp": parse_date(item.get("install_time", "")),
                    "metadata": {
                        "app_name": item.get("app_name", item.get("label", "")),
                        "package_name": item.get("package_name", item.get("package", "")),
                        "version": item.get("version", "1.0.0"),
                        "raw_data": item
                    }
                })
        except Exception:
            pass
        return records

# --- 7. WiFi & Bluetooth Parser ---
class WiFiParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "WiFi"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json", ".csv"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        return "wifi" in os.path.basename(file_path).lower()

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                records.append({
                    "timestamp": parse_date(item.get("last_connected", "")),
                    "metadata": {
                        "ssid": item.get("ssid", "Unknown"),
                        "bssid": item.get("bssid", "00:00:00:00:00:00"),
                        "security": item.get("security", "WPA2"),
                        "raw_data": item
                    }
                })
        except Exception:
            pass
        return records

class BluetoothParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "Bluetooth"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json", ".csv"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        return "bluetooth" in os.path.basename(file_path).lower()

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                records.append({
                    "timestamp": parse_date(item.get("last_seen", "")),
                    "metadata": {
                        "name": item.get("name", "Unknown Device"),
                        "mac_address": item.get("mac_address", item.get("address", "")),
                        "device_class": item.get("device_class", "Audio/Headset"),
                        "raw_data": item
                    }
                })
        except Exception:
            pass
        return records

# --- 8. Notifications Parser ---
class NotificationsParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "Notification"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json", ".csv"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        return "notification" in os.path.basename(file_path).lower()

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                records.append({
                    "timestamp": parse_date(item.get("timestamp", "")),
                    "metadata": {
                        "package_name": item.get("package_name", ""),
                        "title": item.get("title", ""),
                        "text": item.get("text", ""),
                        "raw_data": item
                    }
                })
        except Exception:
            pass
        return records

# --- 9. Device Information Parser ---
class DeviceInformationParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "DeviceInformation"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json", ".txt"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        return "device" in os.path.basename(file_path).lower()

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append({
                    "timestamp": datetime.datetime.utcnow(),
                    "metadata": {
                        "device_name": data.get("device_name", data.get("model", "Android Device")),
                        "os_version": data.get("os_version", data.get("release", "12")),
                        "serial_number": data.get("serial_number", data.get("serial", "")),
                        "imei": data.get("imei", ""),
                        "raw_data": data
                    }
                })
            elif ext == ".txt":
                # Handle standard key-value files
                props = {}
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "=" in line:
                            k, v = line.split("=", 1)
                            props[k.strip()] = v.strip()
                records.append({
                    "timestamp": datetime.datetime.utcnow(),
                    "metadata": {
                        "device_name": props.get("ro.product.model", props.get("model", "Android Device")),
                        "os_version": props.get("ro.build.version.release", props.get("os", "12")),
                        "serial_number": props.get("ro.serialno", props.get("serial", "")),
                        "raw_data": props
                    }
                })
        except Exception:
            pass
        return records

# --- 10. Timeline Events Parser ---
class TimelineEventsParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "TimelineEvent"

    @property
    def supported_extensions(self) -> List[str]:
        return [".json", ".csv"]

    @property
    def priority(self) -> int:
        return 10

    def validate(self, file_path: str) -> bool:
        return "timeline" in os.path.basename(file_path).lower()

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                records.append({
                    "timestamp": parse_date(item.get("timestamp", "")),
                    "metadata": {
                        "event_type": item.get("event_type", "Generic"),
                        "description": item.get("description", ""),
                        "confidence": float(item.get("confidence", 0.5)),
                        "raw_data": item
                    }
                })
        except Exception:
            pass
        return records

# --- 11. Media Metadata Parser ---
class MediaMetadataParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "File"

    @property
    def supported_extensions(self) -> List[str]:
        return [".jpg", ".jpeg", ".png", ".heic", ".mp4", ".avi", ".mov", ".mp3", ".wav", ".aac"]

    @property
    def priority(self) -> int:
        return 5

    def validate(self, file_path: str) -> bool:
        # Matches media extensions
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        ext = os.path.splitext(file_path)[1].lower()
        try:
            h = HashService.calculate_sha256_file(file_path)
            metadata = {}
            if ext in [".jpg", ".jpeg", ".png", ".heic"]:
                metadata = MetadataExtractor.extract_image_metadata(file_path, h)
            elif ext in [".mp4", ".avi", ".mov"]:
                metadata = MetadataExtractor.extract_video_metadata(file_path, h)
            elif ext in [".mp3", ".wav", ".aac"]:
                metadata = MetadataExtractor.extract_audio_metadata(file_path, h)
            
            # Use timestamp extracted, or default to file creation/modification date
            t_str = metadata.get("timestamp")
            t = parse_date(t_str) if t_str else datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            
            records.append({
                "timestamp": t,
                "metadata": metadata
            })
        except Exception:
            pass
        return records

# --- 12. SQLite Database Parser ---
class SQLiteDatabaseParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "SQLiteDatabase"

    @property
    def supported_extensions(self) -> List[str]:
        return [".db", ".sqlite", ".sqlite3"]

    @property
    def priority(self) -> int:
        return 2

    def validate(self, file_path: str) -> bool:
        # Checks if it starts with SQLite header (magic bytes verified)
        try:
            with open(file_path, "rb") as f:
                header = f.read(15)
            return header == b"SQLite format 3"
        except Exception:
            return False

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            
            schema_info = {}
            for t in tables:
                cursor.execute(f"PRAGMA table_info({t});")
                cols = [col[1] for col in cursor.fetchall()]
                cursor.execute(f"SELECT COUNT(*) FROM {t};")
                count = cursor.fetchone()[0]
                schema_info[t] = {
                    "columns": cols,
                    "row_count": count
                }
            
            conn.close()
            
            h = HashService.calculate_sha256_file(file_path)
            records.append({
                "timestamp": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                "metadata": {
                    "filename": os.path.basename(file_path),
                    "filesize": os.path.getsize(file_path),
                    "sha256": h,
                    "tables_found": tables,
                    "schema": schema_info
                }
            })
        except Exception:
            pass
        return records

# --- 13. System Logs Parser ---
class SystemLogsParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "SystemLogs"

    @property
    def supported_extensions(self) -> List[str]:
        return [".log", ".txt"]

    @property
    def priority(self) -> int:
        return 2

    def validate(self, file_path: str) -> bool:
        basename = os.path.basename(file_path).lower()
        return "log" in basename or "system" in basename or "audit" in basename

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            lines = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Read first 100 lines to avoid bloating the DB for massive logs
                for _ in range(500):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.strip())
            
            h = HashService.calculate_sha256_file(file_path)
            records.append({
                "timestamp": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                "metadata": {
                    "filename": os.path.basename(file_path),
                    "filesize": os.path.getsize(file_path),
                    "sha256": h,
                    "log_preview": lines,
                    "total_preview_lines": len(lines)
                }
            })
        except Exception:
            pass
        return records

# --- 14. File Metadata Parser (Fallback) ---
class FileMetadataParser(BaseParser):
    @property
    def artifact_type(self) -> str:
        return "File"

    @property
    def supported_extensions(self) -> List[str]:
        return ["*"]

    @property
    def priority(self) -> int:
        return 1

    def validate(self, file_path: str) -> bool:
        return True # Catch-all

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        records = []
        try:
            h = HashService.calculate_sha256_file(file_path)
            records.append({
                "timestamp": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                "metadata": {
                    "filename": os.path.basename(file_path),
                    "filesize": os.path.getsize(file_path),
                    "sha256": h,
                    "extension": os.path.splitext(file_path)[1]
                }
            })
        except Exception:
            pass
        return records

# --- Auto Registration ---
ParserRegistry.register(ContactsParser())
ParserRegistry.register(SMSParser())
ParserRegistry.register(CallLogParser())
ParserRegistry.register(BrowserHistoryParser())
ParserRegistry.register(GPSParser())
ParserRegistry.register(InstalledAppsParser())
ParserRegistry.register(WiFiParser())
ParserRegistry.register(BluetoothParser())
ParserRegistry.register(NotificationsParser())
ParserRegistry.register(DeviceInformationParser())
ParserRegistry.register(TimelineEventsParser())
ParserRegistry.register(MediaMetadataParser())
ParserRegistry.register(SQLiteDatabaseParser())
ParserRegistry.register(SystemLogsParser())
ParserRegistry.register(FileMetadataParser())
