"""
User Management API — Admin-only endpoints for managing platform users.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.all import User
from app.repositories.all import UserRepository, CaseRepository, EvidenceRepository, AuditLogRepository
from app.schemas.all import UserCreate, UserResponse, UserUpdate
from app.api.deps import get_current_user, RoleChecker
from app.core.audit import log_action

router = APIRouter()

admin_only = RoleChecker(["Admin"])

@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """List all users with pagination — Admin only."""
    users = UserRepository.list_all(db, skip=skip, limit=limit)
    total = UserRepository.count_all(db)
    return users

@router.get("/stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Get platform-wide statistics — Admin only."""
    return {
        "total_users": UserRepository.count_all(db),
        "total_cases": CaseRepository.count_all(db),
        "total_audit_logs": AuditLogRepository.count_all(db),
    }

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Get a specific user — Admin only."""
    user = UserRepository.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Create a new user — Admin only."""
    existing = UserRepository.get_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role or "Investigator"
    )
    UserRepository.create(db, user)
    log_action(db, current_user.id, "ADMIN_CREATE_USER", f"Created user '{user.email}' with role '{user.role}'")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Update user role or name — Admin only. Cannot change own role."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account via admin panel")
    
    user = UserRepository.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_in.name is not None:
        user.name = user_in.name
    if user_in.role is not None:
        valid_roles = ["Investigator", "Admin", "Auditor"]
        if user_in.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Role must be one of: {valid_roles}")
        user.role = user_in.role
    if user_in.password is not None and user_in.password.strip():
        user.password_hash = get_password_hash(user_in.password)
    
    UserRepository.update(db)
    log_action(db, current_user.id, "ADMIN_UPDATE_USER", f"Updated user '{user.email}' (role: {user.role})")
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """Delete a user — Admin only. Cannot delete own account."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = UserRepository.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    email = user.email
    UserRepository.delete(db, user)
    log_action(db, current_user.id, "ADMIN_DELETE_USER", f"Deleted user '{email}'")
    return {"message": f"User '{email}' deleted successfully"}
