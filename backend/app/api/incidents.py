from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import Incident, User
from app.repositories.all import IncidentRepository, CaseRepository
from app.schemas.all import IncidentCreate, IncidentUpdate, IncidentResponse
from app.api.deps import get_current_user
from app.core.audit import log_action

router = APIRouter()

@router.get("", response_model=List[IncidentResponse])
def get_incidents(
    case_id: str = Query(None, description="Filter by case ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "Admin":
        if case_id:
            return IncidentRepository.list_by_case(db, case_id)
        return IncidentRepository.list_all(db)
    
    if case_id:
        # Verify access to the case
        case = CaseRepository.get(db, case_id)
        if case and current_user.role == "Investigator" and case.investigator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this case")
        return IncidentRepository.list_by_case(db, case_id)
    
    return IncidentRepository.list_by_investigator(db, current_user.id)


@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # If case_id provided, verify case exists and user has access
    if incident_in.case_id:
        case = CaseRepository.get(db, incident_in.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        if current_user.role == "Investigator" and case.investigator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this case")

    incident_obj = Incident(
        title=incident_in.title,
        description=incident_in.description,
        incident_type=incident_in.incident_type or "General",
        severity=incident_in.severity or "Medium",
        status="Open",
        investigator_id=current_user.id,
        case_id=incident_in.case_id
    )
    IncidentRepository.create(db, incident_obj)
    
    log_action(db, current_user.id, "CREATE_INCIDENT", f"Created incident '{incident_obj.title}' (Type: {incident_obj.incident_type}, Severity: {incident_obj.severity})")
    
    return incident_obj


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = IncidentRepository.get(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if current_user.role == "Investigator":
        if incident.case_id:
            case = CaseRepository.get(db, incident.case_id)
            if case and case.investigator_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to access this incident")
        elif incident.investigator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this incident")
    
    return incident


@router.put("/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: str,
    incident_in: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = IncidentRepository.get(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if current_user.role == "Investigator":
        if incident.case_id:
            case = CaseRepository.get(db, incident.case_id)
            if case and case.investigator_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to edit this incident")
        elif incident.investigator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to edit this incident")

    if incident_in.title is not None:
        incident.title = incident_in.title
    if incident_in.description is not None:
        incident.description = incident_in.description
    if incident_in.incident_type is not None:
        incident.incident_type = incident_in.incident_type
    if incident_in.severity is not None:
        incident.severity = incident_in.severity
    if incident_in.status is not None:
        incident.status = incident_in.status
    if incident_in.case_id is not None:
        # Verify case exists if linking
        if incident_in.case_id:
            case = CaseRepository.get(db, incident_in.case_id)
            if not case:
                raise HTTPException(status_code=404, detail="Linked case not found")
        incident.case_id = incident_in.case_id

    IncidentRepository.update(db)
    log_action(db, current_user.id, "UPDATE_INCIDENT", f"Updated incident '{incident.title}' status to '{incident.status}'")
    
    return incident


@router.delete("/{incident_id}")
def delete_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incident = IncidentRepository.get(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if current_user.role != "Admin" and incident.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this incident")

    IncidentRepository.delete(db, incident)
    log_action(db, current_user.id, "DELETE_INCIDENT", f"Deleted incident '{incident.title}' (ID: {incident_id})")
    
    return {"message": "Incident deleted successfully"}
