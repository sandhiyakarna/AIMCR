from sqlalchemy.orm import Session
from app.models.all import AuditLog
from app.repositories.all import AuditLogRepository

def log_action(db: Session, user_id: str, action: str, details: str = None) -> AuditLog:
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )
    return AuditLogRepository.create(db, log_entry)
