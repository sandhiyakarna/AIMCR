import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.correlator import CorrelationEngine
from app.services.anomaly_detector import AnomalyDetectorService

class CrimeReconstructionEngine:
    @staticmethod
    def reconstruct_crime(db: Session, case_id: str) -> List[Dict[str, Any]]:
        # 1. Get correlated chains
        chains = CorrelationEngine.correlate_evidence(db, case_id)
        
        # 2. Get behavioral anomalies
        anomalies = AnomalyDetectorService.detect_anomalies(db, case_id)
        
        reconstructions = []
        
        # Scenario A: Phishing & Account Takeover Reconstruction
        phishing_chains = [c for c in chains if c["type"] == "Phishing Sequence"]
        for idx, pc in enumerate(phishing_chains):
            events = pc["events"]
            steps = []
            
            # Map events to sequence steps
            for step_num, ev in enumerate(events, 1):
                meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
                desc = ""
                if ev.artifact_type == "SMS":
                    desc = f"Received SMS: '{meta.get('message', '')}'"
                elif ev.artifact_type == "BrowserHistory":
                    desc = f"Chrome Browser visited URL: {meta.get('url', '')}"
                elif ev.artifact_type == "File":
                    desc = f"File downloaded: {meta.get('filename', '')} ({meta.get('filepath', '')})"
                elif ev.artifact_type == "Application":
                    desc = f"Application opened: {meta.get('app_name', '')}"
                
                # Check for Threat Intel Match or Anti-Forensics indicators
                if "threat_intel_match" in meta:
                    ti = meta["threat_intel_match"]
                    desc += f" [Threat Intel Alert: {ti['threat_name']} ({ti['severity']})]"
                
                if ev.artifact_type == "File" and meta.get("filename", "").endswith(".png") and ("vnd.android.package-archive" in meta.get("mime_type", "") or meta.get("magic_bytes") == "504B0304"):
                    desc += " [Anti-Forensics: Spoofed Extension Detected]"
                
                steps.append({
                    "step_number": step_num,
                    "event_type": ev.artifact_type,
                    "description": desc,
                    "timestamp": ev.timestamp.isoformat(),
                    "evidence_references": [ev.id]
                })
            
            reconstructions.append({
                "incident_type": "SMS Phishing & Account Takeover",
                "confidence": float(pc["confidence"]),
                "explanation": (
                    "A multi-stage intrusion sequence was identified. "
                    "Initially, a SMS message containing an unverified HTTP link was received. "
                    "This link was visited using Chrome browser, leading to a file download containing a potentially "
                    "malicious Android application package (.apk). Subsequently, the user accessed settings and banking applications "
                    "while receiving security OTP messages, which indicates a highly probable credential harvesting and "
                    "unauthorized account takeover attempt."
                ),
                "steps": steps
            })
            
        # Scenario B: Impossible GPS Travel / Spoofing Reconstruction
        gps_anomalies = [a for a in anomalies if a["artifact_type"] == "GPS" and "geographic anomaly" in a["explanation"].lower()]
        if gps_anomalies:
            steps = []
            for step_num, ga in enumerate(gps_anomalies, 1):
                steps.append({
                    "step_number": step_num,
                    "event_type": "GPS Anomaly",
                    "description": f"Geographic jump logged at lat {ga['details'].get('latitude')}, lon {ga['details'].get('longitude')}. {ga['explanation']}",
                    "timestamp": ga["timestamp"].isoformat(),
                    "evidence_references": [ga["evidence_id"]]
                })
            
            reconstructions.append({
                "incident_type": "Geographic Anomaly / Device Spoofing",
                "confidence": 0.90,
                "explanation": (
                    "Device location records indicate physically impossible velocities between consecutive timestamps. "
                    "This deviation suggests likely location spoofing or concurrent session activity indicating that "
                    "multiple entities might have accessed account services from distinct physical locations."
                ),
                "steps": steps
            })

        # Scenario C: Late-night Wallet Access Reconstruction
        wallet_anomalies = [a for a in anomalies if "wallet" in a["explanation"].lower() or "wallet" in str(a["details"].get("app_name", "")).lower()]
        if wallet_anomalies:
            steps = []
            for step_num, wa in enumerate(wallet_anomalies, 1):
                steps.append({
                    "step_number": step_num,
                    "event_type": "App Anomaly",
                    "description": f"Sensitive app access: '{wa['details'].get('app_name')}' opened during typical sleep hours. Anomaly score: {wa['score']:.2f}",
                    "timestamp": wa["timestamp"].isoformat(),
                    "evidence_references": [wa["evidence_id"]]
                })
                
            reconstructions.append({
                "incident_type": "Unusual Sensitive Asset Access",
                "confidence": 0.75,
                "explanation": (
                    "A sensitive local crypto-wallet application was opened during atypical hours (late-night), "
                    "preceded by settings adjustments. This possible unauthorized local file manipulation suggests "
                    "potential device exploitation or unauthorized physical access while the device owner was inactive."
                ),
                "steps": steps
            })
            
        return reconstructions
