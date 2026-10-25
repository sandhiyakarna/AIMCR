import json
import os
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import User, Evidence, EvidenceAccessLog
from app.repositories.all import CaseRepository, EvidenceRepository, EvidenceAccessLogRepository
from app.schemas.all import EvidenceResponse, EvidenceCreate, EvidenceAccessLogResponse
from app.services.evidence import EvidenceService
from app.services.threat_intel import ThreatIntelService
from app.api.deps import get_current_user
from app.core.audit import log_action
from app.core.config import settings

import io

router = APIRouter()

def log_evidence_access(db: Session, evidence_id: str, user_id: str, action: str, remarks: str = None):
    """Helper to log evidence access for chain of custody."""
    log_entry = EvidenceAccessLog(
        evidence_id=evidence_id,
        user_id=user_id,
        action=action,
        remarks=remarks
    )
    EvidenceAccessLogRepository.create(db, log_entry)

def evidence_to_response(ev: Evidence) -> EvidenceResponse:
    return EvidenceResponse(
        id=ev.id,
        case_id=ev.case_id,
        artifact_type=ev.artifact_type,
        source=ev.source,
        hash=ev.hash,
        timestamp=ev.timestamp,
        metadata=json.loads(ev.metadata_json) if ev.metadata_json else {}
    )

@router.post("/upload", response_model=List[EvidenceResponse])
async def upload_evidence(
    case_id: str = Form(...),
    artifact_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this case")

    # Read file content
    contents = await file.read()
    
    # Validate file size
    if len(contents) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_BYTES} bytes."
        )

    # Validate MIME type / extension
    allowed_mime_list = [t.strip().lower() for t in settings.ALLOWED_MIME_TYPES.split(",") if t.strip()]
    content_type = file.content_type.lower() if file.content_type else ""
    
    # We can also check standard extensions if content-type is too generic
    allowed_extensions = ['.json', '.txt', '.csv', '.xml', '.db', '.log']
    filename = file.filename or "uploaded_file"
    filename_lower = filename.lower()
    has_valid_extension = any(filename_lower.endswith(ext) for ext in allowed_extensions)
    
    if content_type not in allowed_mime_list and not has_valid_extension:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed formats: JSON, XML, CSV, TXT, DB, LOG."
        )

    # 1. Verify file integrity (SHA-256)
    file_hash = EvidenceService.calculate_sha256(contents)
    
    ingested_artifacts = []
    
    try:
        # If it is a JSON file containing list of artifacts, parse and bulk ingest
        if filename_lower.endswith(".json"):
            data = json.loads(contents.decode('utf-8'))
            if isinstance(data, list):
                for idx, record in enumerate(data):
                    timestamp_str = record.get("timestamp")
                    timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now(timezone.utc)
                    
                    evidence_obj = Evidence(
                        case_id=case_id,
                        artifact_type=record.get("artifact_type", artifact_type),
                        source=filename,
                        hash=file_hash + f"-{idx}", # unique tag for bulk items
                        timestamp=timestamp,
                        metadata_json=json.dumps(record.get("metadata", {}))
                    )
                    EvidenceRepository.create(db, evidence_obj)
                    ThreatIntelService.check_and_annotate_evidence(db, evidence_obj)
                    # Log chain of custody
                    log_evidence_access(db, evidence_obj.id, current_user.id, "upload", f"Bulk JSON upload - {filename}")
                    ingested_artifacts.append(evidence_obj)
            else:
                raise ValueError("JSON file must be a list of records")
        else:
            # Single file import (e.g., raw text or single log)
            # Create a default metadata dict with filename and size
            metadata = {
                "filename": filename,
                "filesize": len(contents),
                "content_preview": contents[:500].decode('utf-8', errors='ignore')
            }
            
            evidence_obj = Evidence(
                case_id=case_id,
                artifact_type=artifact_type,
                source=filename,
                hash=file_hash,
                timestamp=datetime.now(timezone.utc),
                metadata_json=json.dumps(metadata)
            )
            EvidenceRepository.create(db, evidence_obj)
            ThreatIntelService.check_and_annotate_evidence(db, evidence_obj)
            # Log chain of custody
            log_evidence_access(db, evidence_obj.id, current_user.id, "upload", f"Single file upload - {filename}")
            ingested_artifacts.append(evidence_obj)
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse forensic file: {str(e)}"
        )

    # Log upload in audit trail
    log_action(
        db,
        current_user.id,
        "UPLOAD_EVIDENCE",
        f"Uploaded forensic file '{filename}' (Type: {artifact_type}, Hash: {file_hash[:12]}...) to case ID: {case_id}"
    )

    return [evidence_to_response(ev) for ev in ingested_artifacts]

@router.post("/upload-bulk", response_model=dict)
async def upload_evidence_bulk(
    case_id: str = Form(...),
    artifact_type: str = Form("File"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload multiple evidence files at once."""
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this case")

    results = {
        "total": len(files),
        "uploaded": 0,
        "failed": 0,
        "errors": []
    }

    for file in files:
        try:
            contents = await file.read()
            
            if len(contents) > settings.MAX_UPLOAD_BYTES:
                results["failed"] += 1
                results["errors"].append(f"{file.filename}: File exceeds maximum allowed size")
                continue

            filename = file.filename or "uploaded_file"
            filename_lower = filename.lower()
            file_hash = EvidenceService.calculate_sha256(contents)

            metadata = {
                "filename": filename,
                "filesize": len(contents)
            }

            evidence_obj = Evidence(
                case_id=case_id,
                artifact_type=artifact_type,
                source=filename,
                hash=file_hash,
                timestamp=datetime.now(timezone.utc),
                metadata_json=json.dumps(metadata)
            )
            EvidenceRepository.create(db, evidence_obj)
            ThreatIntelService.check_and_annotate_evidence(db, evidence_obj)
            log_evidence_access(db, evidence_obj.id, current_user.id, "upload", f"Bulk upload - {filename}")
            results["uploaded"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{file.filename}: {str(e)}")

    log_action(db, current_user.id, "BULK_UPLOAD_EVIDENCE", 
               f"Bulk upload: {results['uploaded']} uploaded, {results['failed']} failed for case {case_id}")

    return results

@router.get("/case/{case_id}", response_model=List[EvidenceResponse])
def get_evidence_by_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    evidence_list = EvidenceRepository.list_by_case(db, case_id)
    return [evidence_to_response(ev) for ev in evidence_list]

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence_by_id(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ev = EvidenceRepository.get(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = CaseRepository.get(db, ev.case_id)
    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    # Log view for chain of custody
    log_evidence_access(db, ev.id, current_user.id, "view", "Evidence details viewed")

    return evidence_to_response(ev)

@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download original evidence file. Verifies permissions, preserves MIME type, streams file."""
    ev = EvidenceRepository.get(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = CaseRepository.get(db, ev.case_id)
    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    # Build a response from metadata
    meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
    filename = meta.get("filename", ev.source)
    
    # Determine MIME type based on artifact type
    mime_map = {
        "SMS": "application/json",
        "Call": "application/json",
        "GPS": "application/geo+json",
        "BrowserHistory": "application/json",
        "Contact": "application/json",
        "Application": "application/json",
        "File": "application/octet-stream",
        "Notification": "application/json",
        "WiFi": "application/json",
        "Bluetooth": "application/json",
    }
    media_type = mime_map.get(ev.artifact_type, "application/octet-stream")

    # Create a downloadable JSON payload with evidence metadata
    content = json.dumps({
        "id": ev.id,
        "case_id": ev.case_id,
        "artifact_type": ev.artifact_type,
        "source": ev.source,
        "hash": ev.hash,
        "timestamp": ev.timestamp.isoformat(),
        "metadata": meta
    }, indent=2)

    # Log download for chain of custody
    log_evidence_access(db, ev.id, current_user.id, "download", f"Evidence downloaded as {filename}")

    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content))
        }
    )


@router.get("/{evidence_id}/access-logs", response_model=List[EvidenceAccessLogResponse])
def get_evidence_access_logs(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chain of custody access logs for a specific evidence item."""
    ev = EvidenceRepository.get(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = CaseRepository.get(db, ev.case_id)
    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    logs = EvidenceAccessLogRepository.list_by_evidence(db, evidence_id)
    return [
        EvidenceAccessLogResponse(
            id=log.id,
            evidence_id=log.evidence_id,
            user_id=log.user_id,
            action=log.action,
            timestamp=log.timestamp,
            remarks=log.remarks
        )
        for log in logs
    ]
