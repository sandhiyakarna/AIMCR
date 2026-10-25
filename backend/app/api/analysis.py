from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import User, EvidenceAccessLog
from app.repositories.all import CaseRepository, EvidenceRepository, EvidenceAccessLogRepository
from app.schemas.all import CommunicationGraphResponse, AnomalyResponse
from app.services.anomaly_detector import AnomalyDetectorService
from app.services.graph_engine import GraphEngineService
from app.services.threat_intel import ThreatIntelService
from app.services.anti_forensics import AntiForensicsService
from app.services.risk_scorer import ForensicComplexityService
from app.services.recommendations import ForensicRecommendationsService
from app.api.deps import get_current_user
from app.core.audit import log_action

router = APIRouter()

def log_evidence_access(db: Session, evidence_id: str, user_id: str, action: str, remarks: str = None):
    log_entry = EvidenceAccessLog(
        evidence_id=evidence_id,
        user_id=user_id,
        action=action,
        remarks=remarks
    )
    EvidenceAccessLogRepository.create(db, log_entry)

@router.post("/run/{case_id}")
def run_case_analysis(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this case")

    # 1. Annotate all evidence with Threat Intelligence IOCs
    evidence_list = EvidenceRepository.list_by_case(db, case_id)
    ti_matches = 0
    for ev in evidence_list:
        if ThreatIntelService.check_and_annotate_evidence(db, ev):
            ti_matches += 1
            # Log chain of custody for threat intel analysis
            log_evidence_access(db, ev.id, current_user.id, "analysis", "Threat intelligence check performed")

    # 2. Run behavioral anomalies & graph analysis
    anomalies = AnomalyDetectorService.detect_anomalies(db, case_id)
    graph = GraphEngineService.build_communication_graph(db, case_id)
    
    # Log chain of custody for all evidence accessed during analysis
    for ev in evidence_list:
        log_evidence_access(db, ev.id, current_user.id, "analysis", "Evidence analyzed during case analysis run")
    
    # Log in audit trail
    log_action(
        db,
        current_user.id,
        "RUN_ANALYSIS",
        f"Executed AI behavioral profiling & communication graph analysis for case ID: {case_id}. Detected {len(anomalies)} anomalies and {ti_matches} Threat Intel match(es)."
    )
    
    return {
        "status": "Success",
        "message": "Analysis finished successfully",
        "anomalies_count": len(anomalies),
        "threat_intel_matches_count": ti_matches,
        "graph_nodes_count": len(graph.get("nodes", []))
    }

@router.get("/summary/{case_id}")
def get_case_analysis_summary(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    # Compute metric values
    complexity = ForensicComplexityService.calculate_complexity(db, case_id)
    anti_forensics = AntiForensicsService.detect(db, case_id)
    recs = ForensicRecommendationsService.generate_recommendations(db, case_id)

    return {
        "complexity": complexity,
        "anti_forensics": anti_forensics,
        "recommendations": recs
    }

@router.get("/anomalies/{case_id}", response_model=list[AnomalyResponse])
def get_behavioral_anomalies(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    anomalies = AnomalyDetectorService.detect_anomalies(db, case_id)
    
    return [
        AnomalyResponse(
            evidence_id=a["evidence_id"],
            timestamp=a["timestamp"],
            artifact_type=a["artifact_type"],
            score=a["score"],
            explanation=a["explanation"],
            confidence=a["confidence"],
            details=a["details"]
        )
        for a in anomalies
    ]

@router.get("/graph/{case_id}", response_model=CommunicationGraphResponse)
def get_communication_graph(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    return GraphEngineService.build_communication_graph(db, case_id)
