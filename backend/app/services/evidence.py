import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.all import Evidence
from app.repositories.all import EvidenceRepository

class EvidenceService:
    @staticmethod
    def calculate_sha256(file_bytes: bytes) -> str:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_bytes)
        return sha256_hash.hexdigest()

    @staticmethod
    def normalize(
        db: Session,
        case_id: str,
        artifact_type: str,
        source: str,
        timestamp: datetime,
        metadata: Dict[str, Any],
        file_bytes: bytes = None
    ) -> Evidence:
        # Calculate hash from file bytes or metadata if file is not provided
        if file_bytes:
            file_hash = EvidenceService.calculate_sha256(file_bytes)
        else:
            # Generate deterministic hash based on contents for seeding
            content_str = f"{case_id}-{artifact_type}-{timestamp.isoformat()}-{json.dumps(metadata, sort_keys=True)}"
            file_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()

        evidence_obj = Evidence(
            case_id=case_id,
            artifact_type=artifact_type,
            source=source,
            hash=file_hash,
            timestamp=timestamp,
            metadata_json=json.dumps(metadata)
        )
        return EvidenceRepository.create(db, evidence_obj)

    @staticmethod
    def get_by_case(db: Session, case_id: str) -> List[Evidence]:
        return EvidenceRepository.list_by_case(db, case_id)
