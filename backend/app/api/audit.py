from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import User
from app.repositories.all import AuditLogRepository
from app.schemas.all import AuditLogResponse, AuditLogPaginatedResponse
from app.api.deps import get_current_user, RoleChecker

router = APIRouter()

@router.get("", response_model=AuditLogPaginatedResponse)
def get_audit_trail(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    # Only Admin and Auditor roles are permitted
    current_user: User = Depends(RoleChecker(["Admin", "Auditor"]))
):
    logs = AuditLogRepository.list_all(db, skip=skip, limit=limit)
    total_count = AuditLogRepository.count_all(db)
    
    res = []
    for log in logs:
        res.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_name=log.user.name if log.user else "System",
            action=log.action,
            timestamp=log.timestamp,
            details=log.details
        ))
        
    return AuditLogPaginatedResponse(
        items=res,
        total_count=total_count
    )
