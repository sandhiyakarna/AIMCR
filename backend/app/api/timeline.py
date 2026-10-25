import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import User
from app.repositories.all import CaseRepository, EvidenceRepository
from app.schemas.all import EvidenceResponse, CrimeReconstructionResponse
from app.services.reconstruction import CrimeReconstructionEngine
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/{case_id}", response_model=List[EvidenceResponse])
def get_chronological_timeline(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    # Fetch evidence sorted by timestamp (Repository lists chronologically by default)
    evidence_list = EvidenceRepository.list_by_case(db, case_id)
    return [
        EvidenceResponse(
            id=ev.id,
            case_id=ev.case_id,
            artifact_type=ev.artifact_type,
            source=ev.source,
            hash=ev.hash,
            timestamp=ev.timestamp,
            metadata=json.loads(ev.metadata_json) if ev.metadata_json else {}
        )
        for ev in evidence_list
    ]

@router.get("/reconstruct/{case_id}", response_model=List[CrimeReconstructionResponse])
def get_crime_reconstruction(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    reconstructions = CrimeReconstructionEngine.reconstruct_crime(db, case_id)
    return reconstructions
