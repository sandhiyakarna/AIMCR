import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all import User, Report
from app.repositories.all import CaseRepository
from app.services.report_generator import ReportGeneratorService
from app.api.deps import get_current_user
from app.core.audit import log_action

router = APIRouter()

@router.post("/generate/{case_id}")
def generate_case_pdf_report(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    try:
        pdf_path = ReportGeneratorService.generate_report(db, case_id)
        
        # Log generation in audit trail
        log_action(
            db,
            current_user.id,
            "EXPORT_REPORT",
            f"Generated PDF Investigation Report for Case '{case.title}' (Path: {pdf_path})"
        )
        
        # Get the newly created report record
        report_record = db.query(Report).filter(Report.location == pdf_path).first()
        
        return {
            "status": "Success",
            "message": "Report generated successfully",
            "report_id": report_record.id if report_record else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forensic report: {str(e)}"
        )

@router.get("/download/{report_id}")
def download_pdf_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    case = CaseRepository.get(db, report.case_id)
    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this report")

    if not os.path.exists(report.location):
        raise HTTPException(status_code=404, detail="PDF report file not found on disk")

    filename = f"AIMCR_Forensic_Report_{case.title.replace(' ', '_')}.pdf"
    return FileResponse(
        path=report.location,
        media_type="application/pdf",
        filename=filename
    )

@router.get("/case/{case_id}")
def list_reports_for_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = CaseRepository.get(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role == "Investigator" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    reports = db.query(Report).filter(Report.case_id == case_id).order_by(Report.generated_at.desc()).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "generated_at": r.generated_at,
            "location": r.location
        }
        for r in reports
    ]
