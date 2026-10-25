# backend/modules/device_acquisition/import_service.py

import os
import json
import shutil
import zipfile
import tarfile
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models.all import Evidence
from app.repositories.all import EvidenceRepository
from modules.device_acquisition.parser_router import ParserRouter
from modules.device_acquisition.hash_service import HashService
from modules.device_acquisition.integrity_service import IntegrityService
from modules.device_acquisition.artifact_detector import ArtifactDetector

class ImportService:
    @staticmethod
    def process_and_import_file(
        db: Session,
        case_id: str,
        file_path: str,
        filename: str,
        summary: Dict[str, Any]
    ) -> None:
        """Process a single file, run signature checking, hash, validate, parse, and import."""
        summary["total_files"] += 1
        summary["sha256_generated"] += 1
        
        # 1. Detect format & type
        fmt, artifact_type = ArtifactDetector.detect(file_path)
        
        # 2. Check if format is supported
        if artifact_type == "Unsupported":
            summary["unsupported"] += 1
            summary["skipped_files"].append({
                "file": filename,
                "reason": "Unsupported Artifact Type. Parser not available."
            })
            return
            
        summary["supported"] += 1
        
        # 3. Validate file (integrity, size, magic bytes)
        valid, msg = IntegrityService.validate_file(file_path, fmt)
        if not valid:
            summary["skipped_files"].append({
                "file": filename,
                "reason": f"Integrity check failed: {msg}"
            })
            return

        try:
            # 4. Generate Hash
            file_hash = HashService.calculate_sha256_file(file_path)

            # 5. Parse
            fmt_ref, actual_type, records = ParserRouter.route_and_parse(file_path)
            
            # Media or general files just extract metadata
            if actual_type == "File" or fmt in ["JPEG", "PNG", "HEIC", "MP4", "AVI", "MOV", "MP3", "WAV", "AAC"]:
                summary["metadata_extracted"] += 1

            # 6. Ingest records
            if not records:
                # Ingest single file entry
                evidence_obj = Evidence(
                    case_id=case_id,
                    artifact_type=actual_type,
                    source=filename,
                    hash=file_hash,
                    timestamp=datetime.fromtimestamp(os.path.getmtime(file_path)),
                    metadata_json=json.dumps({
                        "filename": filename,
                        "filesize": os.path.getsize(file_path),
                        "format": fmt,
                        "status": "Imported"
                    })
                )
                EvidenceRepository.create(db, evidence_obj)
                summary["imported_successfully"] += 1
            else:
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
                        artifact_type=actual_type,
                        source=filename,
                        hash=sub_hash,
                        timestamp=rec_time,
                        metadata_json=json.dumps(record.get("metadata", {}))
                    )
                    EvidenceRepository.create(db, evidence_obj)
                    summary["imported_successfully"] += 1

        except Exception as e:
            summary["skipped_files"].append({
                "file": filename,
                "reason": f"Import failed: {str(e)}"
            })

    @classmethod
    def import_evidence(
        cls,
        db: Session,
        case_id: str,
        file_path: str,
        filename: str
    ) -> Dict[str, Any]:
        """Main entry point to import files or ZIP/TAR archives containing files."""
        summary = {
            "total_files": 0,
            "supported": 0,
            "unsupported": 0,
            "imported_successfully": 0,
            "metadata_extracted": 0,
            "sha256_generated": 0,
            "skipped_files": []
        }

        ext = os.path.splitext(filename)[1].lower()
        workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(workspace_dir, f"temp_import_{int(datetime.utcnow().timestamp())}")

        try:
            if ext == ".zip":
                os.makedirs(temp_dir, exist_ok=True)
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Recursively process files
                for root, _, files in os.walk(temp_dir):
                    for f in files:
                        sub_file_path = os.path.join(root, f)
                        rel_path = os.path.relpath(sub_file_path, temp_dir)
                        cls.process_and_import_file(db, case_id, sub_file_path, rel_path, summary)
            
            elif ext in [".tar", ".gz", ".tgz"]:
                os.makedirs(temp_dir, exist_ok=True)
                if ext == ".tar":
                    with tarfile.open(file_path, 'r') as tar_ref:
                        tar_ref.extractall(temp_dir)
                else:
                    # Gzipped tar
                    with tarfile.open(file_path, 'r:gz') as tar_ref:
                        tar_ref.extractall(temp_dir)
                
                for root, _, files in os.walk(temp_dir):
                    for f in files:
                        sub_file_path = os.path.join(root, f)
                        rel_path = os.path.relpath(sub_file_path, temp_dir)
                        cls.process_and_import_file(db, case_id, sub_file_path, rel_path, summary)
            
            else:
                # Single file
                cls.process_and_import_file(db, case_id, file_path, filename, summary)
                
        except Exception as e:
            summary["skipped_files"].append({
                "file": filename,
                "reason": f"Failed to expand or read archive: {str(e)}"
            })
        finally:
            # Cleanup temp directory
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
                    
        return summary
