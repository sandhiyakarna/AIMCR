import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.all import Evidence
from app.repositories.all import EvidenceRepository

class AntiForensicsService:
    @staticmethod
    def detect(db: Session, case_id: str) -> List[Dict[str, Any]]:
        """
        Scans all evidence in a case and flags anti-forensic indicators.
        """
        evidence_list = EvidenceRepository.list_by_case(db, case_id)
        alerts = []

        for ev in evidence_list:
            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
            
            # 1. Extension Spoofing
            spoof_alert = AntiForensicsService._check_extension_spoofing(meta)
            if spoof_alert:
                spoof_alert["evidence_id"] = ev.id
                spoof_alert["timestamp"] = ev.timestamp.isoformat()
                alerts.append(spoof_alert)

            # 2. Time-Stomping
            stomping_alert = AntiForensicsService._check_time_stomping(meta)
            if stomping_alert:
                stomping_alert["evidence_id"] = ev.id
                stomping_alert["timestamp"] = ev.timestamp.isoformat()
                alerts.append(stomping_alert)

            # 3. SQLite DB Anomalies
            db_alert = AntiForensicsService._check_sqlite_anomaly(meta)
            if db_alert:
                db_alert["evidence_id"] = ev.id
                db_alert["timestamp"] = ev.timestamp.isoformat()
                alerts.append(db_alert)

            # 4. Forensic Erasers / GPS Spoofing Apps
            app_alert = AntiForensicsService._check_suspicious_apps(meta)
            if app_alert:
                app_alert["evidence_id"] = ev.id
                app_alert["timestamp"] = ev.timestamp.isoformat()
                alerts.append(app_alert)

        return alerts

    @staticmethod
    def _check_extension_spoofing(meta: Dict[str, Any]) -> Dict[str, Any] | None:
        filename = meta.get("filename", "")
        mime_type = meta.get("mime_type", "")
        magic_bytes = meta.get("magic_bytes", "")
        if not filename:
            return None
            
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext in ["png", "jpg", "jpeg", "gif", "txt"]:
            # Check for APK signature disguised as a common user file
            if "vnd.android.package-archive" in mime_type or magic_bytes == "504B0304":
                return {
                    "type": "Extension Spoofing",
                    "severity": "High",
                    "description": f"File '{filename}' has a '{ext}' extension but contains signatures matching an Android application package (.apk)."
                }
        return None

    @staticmethod
    def _check_time_stomping(meta: Dict[str, Any]) -> Dict[str, Any] | None:
        created_time = meta.get("created_time")
        modified_time = meta.get("modified_time")
        filename = meta.get("filename", "")
        if created_time and modified_time:
            try:
                # Check for classic UNIX Epoch 0 (tampered/zeroed modified time)
                if "1970-01-01" in modified_time:
                    return {
                        "type": "Time-Stomping Detected",
                        "severity": "High",
                        "description": f"File '{filename}' modification timestamp is set to UNIX Epoch 0 (1970-01-01), indicating deliberate metadata deletion."
                    }
                
                # Check if modified date is earlier than creation date
                # Strip trailing 'Z' or replace it with offset
                c_str = created_time.replace("Z", "+00:00")
                m_str = modified_time.replace("Z", "+00:00")
                created_dt = datetime.fromisoformat(c_str)
                modified_dt = datetime.fromisoformat(m_str)
                
                if modified_dt < created_dt:
                    return {
                        "type": "Time-Stomping Detected",
                        "severity": "Medium",
                        "description": f"File '{filename}' modification timestamp ({modified_dt.strftime('%Y-%m-%d %H:%M:%S')}) precedes creation timestamp ({created_dt.strftime('%Y-%m-%d %H:%M:%S')})."
                    }
            except Exception:
                pass
        return None

    @staticmethod
    def _check_sqlite_anomaly(meta: Dict[str, Any]) -> Dict[str, Any] | None:
        is_sqlite = meta.get("is_sqlite")
        filename = meta.get("filename", "")
        filesize = meta.get("filesize", 0)
        tables = meta.get("tables")
        
        # Trigger if explicitly marked as SQLite or ends with .db/sqlite extension
        if is_sqlite or filename.endswith(".db") or filename.endswith(".sqlite"):
            if tables == [] or filesize == 0:
                return {
                    "type": "SQLite DB Tampering",
                    "severity": "High",
                    "description": f"SQLite database file '{filename}' was found with 0 bytes or empty tables, indicating potential table purging or record wiping."
                }
        return None

    @staticmethod
    def _check_suspicious_apps(meta: Dict[str, Any]) -> Dict[str, Any] | None:
        app_name = meta.get("app_name", "")
        known_cleaners = {
            "com.piriform.ccleaner": "CCleaner (Cache/Artifact Eraser)",
            "com.lexa.fakegps": "Fake GPS location spoofer",
            "com.fakegps.mock": "GPS Mock location spoofer",
            "cn.lm.cleaner": "Clean Master eraser",
            "com.sublimis.uranium": "Titanium Backup manager"
        }
        if app_name in known_cleaners:
            return {
                "type": "Eraser Application Launched",
                "severity": "Medium",
                "description": f"Suspicious anti-forensics application launched: {known_cleaners[app_name]} ({app_name})."
            }
        return None
