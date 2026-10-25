# backend/modules/device_acquisition/acquisition_service.py

import os
import json
import shutil
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.all import Evidence
from app.repositories.all import EvidenceRepository
from modules.device_acquisition.adb_manager import ADBManager
from modules.device_acquisition.parser_router import ParserRouter
from modules.device_acquisition.hash_service import HashService

class AcquisitionService:
    @staticmethod
    def acquire_device(db: Session, case_id: str, device_id: str) -> Dict[str, Any]:
        """Scans, pulls, parses, and ingests all accessible files from an Android device."""
        summary = {
            "device_id": device_id,
            "status": "Success",
            "files_found": 0,
            "files_pulled": 0,
            "records_imported": 0,
            "errors": []
        }

        # Validate device connection
        devices = ADBManager.list_devices()
        selected_device = next((d for d in devices if d["id"] == device_id), None)
        if not selected_device:
            summary["status"] = "Failed"
            summary["errors"].append(f"Device {device_id} not found or disconnected.")
            return summary
        if selected_device["status"] != "device":
            summary["status"] = "Failed"
            summary["errors"].append(f"Device {device_id} is unauthorized or offline.")
            return summary

        # Create temporary working directory inside the workspace
        workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(workspace_dir, f"temp_acquisition_{device_id}_{int(datetime.now(timezone.utc).timestamp())}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            remote_paths = ADBManager.scan_accessible_artifacts(device_id)
            summary["files_found"] = len(remote_paths)

            for remote_path in remote_paths:
                filename = os.path.basename(remote_path)
                local_path = os.path.join(temp_dir, filename)

                # Pull the file
                pulled = ADBManager.acquire_file(device_id, remote_path, local_path)
                if not pulled:
                    summary["errors"].append(f"Could not pull {remote_path}")
                    continue
                summary["files_pulled"] += 1

                # Calculate SHA-256
                file_hash = HashService.calculate_sha256_file(local_path)

                # Route and parse
                fmt, artifact_type, records = ParserRouter.route_and_parse(local_path)

                # Ingest records
                if not records:
                    # Ingest file metadata if no specific parser returned records
                    evidence_obj = Evidence(
                        case_id=case_id,
                        artifact_type=artifact_type,
                        source=filename,
                        hash=file_hash,
                        timestamp=datetime.fromtimestamp(os.path.getmtime(local_path)),
                        metadata_json=json.dumps({
                            "filename": filename,
                            "filesize": os.path.getsize(local_path),
                            "format": fmt,
                            "note": "Imported as raw file / generic schema"
                        })
                    )
                    EvidenceRepository.create(db, evidence_obj)
                    summary["records_imported"] += 1
                else:
                    # If multiple records, ingest each
                    for idx, record in enumerate(records):
                        sub_hash = f"{file_hash}-{idx}"
                        rec_time = record.get("timestamp")
                        if isinstance(rec_time, str):
                            try:
                                rec_time = datetime.fromisoformat(rec_time)
                            except Exception:
                                rec_time = datetime.now(timezone.utc)
                        elif not isinstance(rec_time, datetime):
                            rec_time = datetime.now(timezone.utc)

                        evidence_obj = Evidence(
                            case_id=case_id,
                            artifact_type=artifact_type,
                            source=filename,
                            hash=sub_hash,
                            timestamp=rec_time,
                            metadata_json=json.dumps(record.get("metadata", {}))
                        )
                        EvidenceRepository.create(db, evidence_obj)
                        summary["records_imported"] += 1

        except Exception as e:
            summary["status"] = "Failed"
            summary["errors"].append(f"Acquisition crashed: {str(e)}")
        finally:
            # Clean up temp folder
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        return summary
