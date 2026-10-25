import json
from sqlalchemy.orm import Session
from app.services.anti_forensics import AntiForensicsService
from app.services.anomaly_detector import AnomalyDetectorService
from app.repositories.all import EvidenceRepository

class ForensicComplexityService:
    @staticmethod
    def calculate_complexity(db: Session, case_id: str) -> dict:
        """
        Calculates the Forensic Case Complexity Index (FCCI) (0-100)
        and returns the classification rating and breakdown.
        """
        evidence_list = EvidenceRepository.list_by_case(db, case_id)
        
        # 1. Threat Intel Matches
        threat_intel_count = 0
        for ev in evidence_list:
            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
            if "threat_intel_match" in meta:
                threat_intel_count += 1
                
        # 2. Anti-Forensic Alerts
        anti_forensics_alerts = AntiForensicsService.detect(db, case_id)
        anti_forensics_count = len(anti_forensics_alerts)
        
        # 3. Behavioral Anomalies
        anomalies = AnomalyDetectorService.detect_anomalies(db, case_id)
        anomaly_count = len(anomalies)
        
        # 4. Hash Integrity Status
        # For simplicity, if any evidence is missing a hash or hash is malformed, flag it.
        # Otherwise, check if hash is verified.
        integrity_failures = 0
        for ev in evidence_list:
            if not ev.hash or len(ev.hash) < 32:
                integrity_failures += 1
        
        # Scoring Model
        threat_score = min(threat_intel_count * 25, 50)
        anti_forensic_score = min(anti_forensics_count * 20, 40)
        anomaly_score = min(anomaly_count * 10, 30)
        integrity_score = 10 if integrity_failures > 0 else 0
        
        fcci = min(threat_score + anti_forensic_score + anomaly_score + integrity_score, 100)
        
        # Classification
        if fcci <= 25:
            rating = "Low"
        elif fcci <= 50:
            rating = "Medium"
        elif fcci <= 75:
            rating = "High"
        else:
            rating = "Critical"
            
        # Explanations breakdown
        factors = []
        if threat_intel_count > 0:
            factors.append(f"Matched {threat_intel_count} Threat Intelligence indicator(s) (+{threat_score} pts)")
        if anti_forensics_count > 0:
            factors.append(f"Identified {anti_forensics_count} active anti-forensics attempt(s) (+{anti_forensic_score} pts)")
        if anomaly_count > 0:
            factors.append(f"Flagged {anomaly_count} behavioral anomalies (+{anomaly_score} pts)")
        if integrity_failures > 0:
            factors.append(f"Detected {integrity_failures} file integrity issue(s) (+{integrity_score} pts)")
            
        if not factors:
            factors.append("No critical digital forensic indicators or compromises detected.")
            
        return {
            "score": fcci,
            "rating": rating,
            "threat_intel_matches": threat_intel_count,
            "anti_forensics_alerts": anti_forensics_count,
            "anomalies_count": anomaly_count,
            "integrity_failures": integrity_failures,
            "breakdown": factors,
            "explanation": f"Case analysis yields a {rating} Forensic Case Complexity Index of {fcci}/100. Breakdown: " + "; ".join(factors)
        }
