import json
from sqlalchemy.orm import Session
from app.models.all import Evidence, ThreatIndicator

class ThreatIntelService:
    @staticmethod
    def check_and_annotate_evidence(db: Session, evidence: Evidence) -> bool:
        """
        Check evidence against threat indicators table.
        If matched, annotates evidence.metadata_json with 'threat_intel_match' details.
        Returns True if a match was found and annotated.
        """
        meta = json.loads(evidence.metadata_json) if evidence.metadata_json else {}
        
        # Avoid duplicate checks if already marked
        if "threat_intel_match" in meta:
            return True
            
        match = None
        
        # 1. Match by artifact type
        if evidence.artifact_type == "SMS":
            phone_number = meta.get("phone_number")
            message = meta.get("message", "")
            
            # Check sender phone number
            if phone_number:
                indicator = db.query(ThreatIndicator).filter(
                    ThreatIndicator.indicator_type == "phone_number",
                    ThreatIndicator.value == phone_number
                ).first()
                if indicator:
                    match = indicator
            
            # Check URLs or domains inside the message content
            if not match and message:
                indicators = db.query(ThreatIndicator).filter(
                    ThreatIndicator.indicator_type.in_(["domain", "url"])
                ).all()
                for ind in indicators:
                    if ind.value in message:
                        match = ind
                        break
                        
        elif evidence.artifact_type == "BrowserHistory":
            url = meta.get("url", "")
            if url:
                indicators = db.query(ThreatIndicator).filter(
                    ThreatIndicator.indicator_type.in_(["domain", "url"])
                ).all()
                for ind in indicators:
                    if ind.value in url:
                        match = ind
                        break
                        
        elif evidence.artifact_type == "File":
            # Match by integrity hash
            file_hash = evidence.hash
            if file_hash:
                indicator = db.query(ThreatIndicator).filter(
                    ThreatIndicator.indicator_type == "hash",
                    ThreatIndicator.value == file_hash
                ).first()
                if indicator:
                    match = indicator
            
            # Also check file name/path
            filename = meta.get("filename", "")
            if not match and filename:
                indicator = db.query(ThreatIndicator).filter(
                    ThreatIndicator.indicator_type == "filename",
                    ThreatIndicator.value == filename
                ).first()
                if indicator:
                    match = indicator
                    
        elif evidence.artifact_type == "Application":
            app_name = meta.get("app_name", "")
            if app_name:
                indicator = db.query(ThreatIndicator).filter(
                    ThreatIndicator.indicator_type == "package_name",
                    ThreatIndicator.value == app_name
                ).first()
                if indicator:
                    match = indicator

        if match:
            meta["threat_intel_match"] = {
                "indicator_id": match.id,
                "indicator_type": match.indicator_type,
                "value": match.value,
                "threat_name": match.threat_name,
                "severity": match.severity,
                "description": match.description
            }
            evidence.metadata_json = json.dumps(meta)
            db.add(evidence)
            db.commit()
            return True
            
        return False
