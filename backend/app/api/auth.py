from datetime import timedelta, datetime, timezone
import secrets
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.all import User
from app.repositories.all import UserRepository
from app.schemas.all import UserCreate, UserResponse, Token, SecureAccessStart, SecureAccessVerify, PasswordResetRequest, PasswordResetConfirm
from app.api.deps import get_current_user
from app.core.audit import log_action

router = APIRouter()

OFFICIAL_RANKS = {"SI", "Commissioner", "AC", "DC", "ASP", "DSP", "Inspector", "Constable", "Investigator", "Admin", "Auditor"}
_access_challenges: Dict[str, dict] = {}
_reset_challenges: Dict[str, dict] = {}

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if user_in.role not in OFFICIAL_RANKS:
        raise HTTPException(status_code=400, detail="Select a valid official designation")
    db_user = UserRepository.get_by_email(db, user_in.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_in.password)
    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_password,
        role=user_in.role
    )
    UserRepository.create(db, user)
    
    # Log registration in audit log
    log_action(db, user.id, "REGISTER_USER", f"Registered new user '{user.email}' with role '{user.role}'")
    
    return user

@router.post("/secure-access/start")
def start_secure_access(payload: SecureAccessStart, db: Session = Depends(get_db)):
    user = UserRepository.get_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    challenge_id = secrets.token_urlsafe(32)
    _access_challenges[challenge_id] = {
        "user_id": user.id,
        "created_at": datetime.now(timezone.utc),
        "mfa_code": "246810"  # Demonstration challenge; replace with an OTP provider in production.
    }
    return {"challenge_id": challenge_id, "mfa_delivery": "demonstration", "mfa_code_hint": "246810"}

@router.post("/secure-access/verify", response_model=Token)
def verify_secure_access(payload: SecureAccessVerify, db: Session = Depends(get_db)):
    challenge = _access_challenges.pop(payload.challenge_id, None)
    if not challenge or (datetime.now(timezone.utc) - challenge["created_at"]).total_seconds() > 300:
        raise HTTPException(status_code=400, detail="Security challenge expired. Start again.")
    if payload.mfa_code != challenge["mfa_code"]:
        raise HTTPException(status_code=400, detail="MFA verification failed")
    if payload.biometric_assertion not in {"webauthn", "biometric-simulation"}:
        raise HTTPException(status_code=400, detail="Biometric verification failed")
    if payload.dsc_assertion != "dsc-token-simulation":
        raise HTTPException(status_code=400, detail="DSC token verification failed")
    user = db.query(User).filter(User.id == challenge["user_id"]).first()
    access_token = create_access_token(subject=user.id, role=user.role, expires_delta=timedelta(minutes=60))
    log_action(db, user.id, "SECURE_ACCESS_GRANTED", f"MFA, biometric, and DSC verification completed for {user.email}")
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "name": user.name}

@router.post("/password-recovery/request")
def request_password_recovery(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = UserRepository.get_by_email(db, payload.email)
    response = {"message": "If the address is registered, recovery instructions have been issued."}
    if user:
        reset_token = secrets.token_urlsafe(32)
        _reset_challenges[reset_token] = {"user_id": user.id, "created_at": datetime.now(timezone.utc)}
        response["demonstration_reset_token"] = reset_token
    return response

@router.post("/password-recovery/confirm")
def confirm_password_recovery(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    challenge = _reset_challenges.pop(payload.reset_token, None)
    if not challenge or (datetime.now(timezone.utc) - challenge["created_at"]).total_seconds() > 900:
        raise HTTPException(status_code=400, detail="Recovery request expired")
    user = db.query(User).filter(User.id == challenge["user_id"]).first()
    user.password_hash = get_password_hash(payload.password)
    db.commit()
    log_action(db, user.id, "PASSWORD_RESET", f"Password reset completed for {user.email}")
    return {"message": "Password updated. Continue with secure access."}

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = UserRepository.get_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
        
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        expires_delta=timedelta(minutes=60)
    )
    
    # Log login in audit log
    log_action(db, user.id, "LOGIN", f"User {user.email} logged in successfully")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
