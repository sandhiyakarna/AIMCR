from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.all import User, Case, Evidence, AuditLog, BehaviorProfile, TimelineEvent, Report, Incident, EvidenceAccessLog

class UserRepository:
    @staticmethod
    def get(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update(db: Session) -> None:
        db.commit()

    @staticmethod
    def delete(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(User).count()

class CaseRepository:
    @staticmethod
    def get(db: Session, case_id: str) -> Optional[Case]:
        return db.query(Case).filter(Case.id == case_id).first()

    @staticmethod
    def list_by_investigator(db: Session, investigator_id: str, skip: int = 0, limit: int = 100) -> List[Case]:
        return (
            db.query(Case)
            .filter(Case.investigator_id == investigator_id)
            .order_by(Case.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Case]:
        return db.query(Case).order_by(Case.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count_by_investigator(db: Session, investigator_id: str) -> int:
        return db.query(Case).filter(Case.investigator_id == investigator_id).count()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(Case).count()

    @staticmethod
    def create(db: Session, case_obj: Case) -> Case:
        db.add(case_obj)
        db.commit()
        db.refresh(case_obj)
        return case_obj

    @staticmethod
    def update(db: Session) -> None:
        db.commit()

    @staticmethod
    def delete(db: Session, case_obj: Case) -> None:
        db.delete(case_obj)
        db.commit()

class IncidentRepository:
    @staticmethod
    def get(db: Session, incident_id: str) -> Optional[Incident]:
        return db.query(Incident).filter(Incident.id == incident_id).first()

    @staticmethod
    def list_by_investigator(db: Session, investigator_id: str, skip: int = 0, limit: int = 100) -> List[Incident]:
        return (
            db.query(Incident)
            .filter(Incident.investigator_id == investigator_id)
            .order_by(Incident.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_by_case(db: Session, case_id: str, skip: int = 0, limit: int = 100) -> List[Incident]:
        return (
            db.query(Incident)
            .filter(Incident.case_id == case_id)
            .order_by(Incident.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Incident]:
        return db.query(Incident).order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(Incident).count()

    @staticmethod
    def create(db: Session, incident_obj: Incident) -> Incident:
        db.add(incident_obj)
        db.commit()
        db.refresh(incident_obj)
        return incident_obj

    @staticmethod
    def update(db: Session) -> None:
        db.commit()

    @staticmethod
    def delete(db: Session, incident_obj: Incident) -> None:
        db.delete(incident_obj)
        db.commit()

class EvidenceRepository:
    @staticmethod
    def get(db: Session, evidence_id: str) -> Optional[Evidence]:
        return db.query(Evidence).filter(Evidence.id == evidence_id).first()

    @staticmethod
    def list_by_case(db: Session, case_id: str, skip: int = 0, limit: int = 500) -> List[Evidence]:
        return (
            db.query(Evidence)
            .filter(Evidence.case_id == case_id)
            .order_by(Evidence.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_by_case(db: Session, case_id: str) -> int:
        return db.query(Evidence).filter(Evidence.case_id == case_id).count()

    @staticmethod
    def create(db: Session, evidence_obj: Evidence) -> Evidence:
        db.add(evidence_obj)
        db.commit()
        db.refresh(evidence_obj)
        return evidence_obj

    @staticmethod
    def create_bulk(db: Session, evidence_objs: List[Evidence]) -> List[Evidence]:
        db.add_all(evidence_objs)
        db.commit()
        return evidence_objs

class EvidenceAccessLogRepository:
    @staticmethod
    def get(db: Session, log_id: str) -> Optional[EvidenceAccessLog]:
        return db.query(EvidenceAccessLog).filter(EvidenceAccessLog.id == log_id).first()

    @staticmethod
    def list_by_evidence(db: Session, evidence_id: str, skip: int = 0, limit: int = 100) -> List[EvidenceAccessLog]:
        return (
            db.query(EvidenceAccessLog)
            .filter(EvidenceAccessLog.evidence_id == evidence_id)
            .order_by(EvidenceAccessLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[EvidenceAccessLog]:
        return db.query(EvidenceAccessLog).order_by(EvidenceAccessLog.timestamp.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, log: EvidenceAccessLog) -> EvidenceAccessLog:
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(EvidenceAccessLog).count()

class AuditLogRepository:
    @staticmethod
    def create(db: Session, log: AuditLog) -> AuditLog:
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(AuditLog).count()
