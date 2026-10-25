from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import User
from app.repositories.all import CaseRepository
from app.schemas.all import CopilotQuery, CopilotResponse, EvidenceResponse, AIQueryRequest, AIQueryResponse
from app.services.copilot import CopilotService
from app.api.deps import get_current_user
from app.core.audit import log_action
import json

router = APIRouter()

@router.post("/chat", response_model=CopilotResponse)
def ask_copilot(
    query_in: CopilotQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, query_in.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    # Call Copilot RAG service
    result = CopilotService.ask(db, query_in.case_id, query_in.question)
    
    # Log the query and response in audit trail
    log_action(
        db,
        current_user.id,
        "QUERY_COPILOT",
        f"Asked Copilot: '{query_in.question}'. Response cited {len(result['retrieved_evidence'])} artifacts."
    )
    
    # Format evidence models to response schemas
    formatted_evidence = [
        EvidenceResponse(
            id=ev.id,
            case_id=ev.case_id,
            artifact_type=ev.artifact_type,
            source=ev.source,
            hash=ev.hash,
            timestamp=ev.timestamp,
            metadata=json.loads(ev.metadata_json) if ev.metadata_json else {}
        )
        for ev in result["retrieved_evidence"]
    ]
    
    return CopilotResponse(
        answer=result["answer"],
        retrieved_evidence=formatted_evidence
    )

@router.post("/investigations/{case_id}/ai/query", response_model=AIQueryResponse)
def query_ai_assistant(
    case_id: str,
    query_in: AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    # Call the new grounded RAG pipeline
    result = CopilotService.query_grounded_ai(db, case_id, query_in.question)
    
    # Log query in system audit log
    log_action(
        db,
        current_user.id,
        "QUERY_AI_ASSISTANT",
        f"Queried AI Assistant: '{query_in.question}' on case ID '{case_id}'"
    )
    
    # Format evidence models to response schemas
    formatted_evidence = [
        EvidenceResponse(
            id=ev.id,
            case_id=ev.case_id,
            artifact_type=ev.artifact_type,
            source=ev.source,
            hash=ev.hash,
            timestamp=ev.timestamp,
            metadata=json.loads(ev.metadata_json) if ev.metadata_json else {}
        )
        for ev in result["retrieved_evidence"]
    ]
    
    return AIQueryResponse(
        answer=result["answer"],
        evidence_references=result["evidence_references"],
        timeline_references=result["timeline_references"],
        confidence=result["confidence"],
        limitations=result["limitations"],
        retrieved_evidence=formatted_evidence
    )

@router.get("/investigations/{case_id}/summary")
def get_case_ai_summary(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    prompt = (
        "Generate a complete investigation summary detailing:\n"
        "- Case Overview\n"
        "- Key Evidence\n"
        "- Significant Timeline Events\n"
        "- Correlated Evidence\n"
        "- Suspicious Activities\n"
        "- Observations\n"
        "- Recommended Next Investigation Steps\n"
        "- Evidence Limitations\n"
    )
    result = CopilotService.query_grounded_ai(db, case_id, prompt)
    return {
        "summary": result["answer"],
        "confidence": result["confidence"],
        "limitations": result["limitations"]
    }

@router.get("/recommendations/{case_id}")
def get_forensic_recommendations(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    from app.services.recommendations import ForensicRecommendationsService
    return ForensicRecommendationsService.generate_recommendations(db, case_id)
