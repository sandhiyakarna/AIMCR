# backend/app/api/acquisition.py

import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.all import User
from app.api.deps import get_current_user
from app.core.audit import log_action

from modules.device_acquisition.device_detector import DeviceDetector
from modules.device_acquisition.acquisition_service import AcquisitionService
from modules.device_acquisition.import_service import ImportService
from modules.device_acquisition.supported_formats import SUPPORTED_EXTENSIONS, MIME_TYPE_MAPPING

router = APIRouter()

# Pydantic models for request bodies
class AcquireRequest(BaseModel):
    case_id: str
    device_id: str

class FileCheckItem(BaseModel):
    filename: str
    mime_type: str

class FileCheckRequest(BaseModel):
    files: List[FileCheckItem]

@router.get("/devices", response_model=List[Dict[str, Any]])
def get_devices(
    current_user: User = Depends(get_current_user)
):
    """Retrieve all physical and emulated connected forensic devices."""
    try:
        return DeviceDetector.get_connected_devices()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan devices: {str(e)}"
        )

@router.post("/acquire", response_model=Dict[str, Any])
def acquire_device(
    payload: AcquireRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger forensic acquisition from a connected device and ingest pulled evidence."""
    # Audit log the acquisition attempt
    log_action(
        db,
        current_user.id,
        "ACQUIRE_DEVICE",
        f"Initiated forensic acquisition for device: {payload.device_id} in case ID: {payload.case_id}"
    )
    
    try:
        summary = AcquisitionService.acquire_device(db, payload.case_id, payload.device_id)
        if summary.get("status") == "Failed":
            raise HTTPException(status_code=400, detail=summary.get("errors", ["Acquisition failed"])[0])
        
        # Log success
        log_action(
            db,
            current_user.id,
            "ACQUIRE_DEVICE_SUCCESS",
            f"Successfully acquired device: {payload.device_id}. Imported {summary.get('records_imported')} records."
        )
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Device acquisition failed: {str(e)}"
        )

@router.post("/check-files", response_model=List[Dict[str, str]])
def check_files(
    payload: FileCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """Check a list of filenames/MIME types and return whether they are supported, unsupported, or metadata only."""
    results = []
    
    # Media file extensions
    media_extensions = {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".avi", ".mov", ".mp3", ".wav", ".aac"}
    
    for item in payload.files:
        filename = item.filename
        ext = os.path.splitext(filename)[1].lower()
        mime = item.mime_type.lower()
        
        # Determine status
        if ext in media_extensions or mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/"):
            # Ensure it is a supported media extension
            if ext in media_extensions:
                status_val = "partially_supported"  # Metadata only
            else:
                status_val = "unsupported"
        elif ext in SUPPORTED_EXTENSIONS or mime in MIME_TYPE_MAPPING:
            status_val = "supported"
        else:
            status_val = "unsupported"
            
        results.append({
            "filename": filename,
            "status": status_val
        })
        
    return results

@router.post("/import", response_model=Dict[str, Any])
async def import_evidence(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a file or archive (ZIP/TAR), extract/parse and ingest forensic evidence."""
    # Write uploaded file bytes to a temporary file inside the workspace
    workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    temp_file_dir = os.path.join(workspace_dir, "temp_uploads")
    os.makedirs(temp_file_dir, exist_ok=True)
    
    temp_file_path = os.path.join(temp_file_dir, f"upload_{int(datetime.now(timezone.utc).timestamp())}_{file.filename}")
    
    try:
        contents = await file.read()
        with open(temp_file_path, "wb") as f:
            f.write(contents)
            
        # Call import service
        summary = ImportService.import_evidence(db, case_id, temp_file_path, file.filename)
        
        # Log audit action
        log_action(
            db,
            current_user.id,
            "IMPORT_EVIDENCE",
            f"Imported forensic file/archive: {file.filename} to case ID: {case_id}. Success: {summary.get('imported_successfully')}, Skipped: {len(summary.get('skipped_files', []))}"
        )
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evidence import failed: {str(e)}"
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
