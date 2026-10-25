from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import Case, User
from app.repositories.all import CaseRepository
from app.schemas.all import CaseCreate, CaseUpdate, CaseResponse
from app.api.deps import get_current_user, RoleChecker
from app.core.audit import log_action

router = APIRouter()

@router.get("", response_model=List[CaseResponse])
def get_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "Admin":
        return CaseRepository.list_all(db)
    return CaseRepository.list_by_investigator(db, current_user.id)

@router.post("", response_model=CaseResponse)
def create_case(
    case_in: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    priority = case_in.priority if case_in.priority in ["Low", "Medium", "High", "Critical"] else "Medium"
    case_obj = Case(
        title=case_in.title,
        description=case_in.description,
        status="Active",
        priority=priority,
        investigator_id=current_user.id
    )
    CaseRepository.create(db, case_obj)
    
    # Log case creation in audit log
    log_action(db, current_user.id, "CREATE_CASE", f"Created case '{case_obj.title}' (ID: {case_obj.id}, Priority: {priority})")
    
    return case_obj

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check permissions (Auditors, Admins can view all; Investigators only their own)
    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
        
    return case

@router.put("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: str,
    case_in: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this case")

    if case_in.title is not None:
        case.title = case_in.title
    if case_in.description is not None:
        case.description = case_in.description
    if case_in.status is not None:
        case.status = case_in.status
    if case_in.priority is not None and case_in.priority in ["Low", "Medium", "High", "Critical"]:
        case.priority = case_in.priority

    CaseRepository.update(db)
    
    # Log update in audit log
    log_action(db, current_user.id, "UPDATE_CASE", f"Updated case '{case.title}' status to '{case.status}' priority to '{case.priority}'")
    
    return case

@router.delete("/{case_id}")
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only Admin or Investigator who owns the case can delete
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if current_user.role != "Admin" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this case")

    CaseRepository.delete(db, case)
    
    # Log deletion in audit log
    log_action(db, current_user.id, "DELETE_CASE", f"Deleted case '{case.title}' (ID: {case_id})")
    
    return {"message": "Case deleted successfully"}
