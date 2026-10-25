import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.all import Evidence, TimelineEvent
from app.repositories.all import EvidenceRepository

class CorrelationEngine:
    @staticmethod
    def extract_domain(url: str) -> str:
        if not url:
            return ""
        # Simple domain extraction
        clean_url = url.replace("http://", "").replace("https://", "").replace("www.", "")
        return clean_url.split("/")[0].split("?")[0]

    @staticmethod
    def correlate_evidence(db: Session, case_id: str) -> List[Dict[str, Any]]:
        evidence_list = EvidenceRepository.list_by_case(db, case_id)
        if not evidence_list:
            return []

        # Sort evidence chronologically
        evidence_list = sorted(evidence_list, key=lambda x: x.timestamp)
        chains = []
        visited = set()

        # Step 1: Detect specific multi-stage attack scenarios
        for i, ev in enumerate(evidence_list):
            if ev.id in visited:
                continue

            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}

            # Phishing Campaign Sequence
            # SMS containing a link -> Visit to that link -> File download -> App launch -> OTP -> Bank transfer
            if ev.artifact_type == "SMS" and "http" in meta.get("message", ""):
                # Potential start of a phishing chain
                chain = [ev]
                visited.add(ev.id)
                msg_text = meta.get("message", "")
                link = next((w for w in msg_text.split() if w.startswith("http")), "")
                domain = CorrelationEngine.extract_domain(link)

                # Search forward in time
                current_time = ev.timestamp
                max_window = timedelta(minutes=30)

                for j in range(i + 1, len(evidence_list)):
                    next_ev = evidence_list[j]
                    if next_ev.id in visited:
                        continue
                    if next_ev.timestamp - current_time > max_window:
                        break

                    next_meta = json.loads(next_ev.metadata_json) if next_ev.metadata_json else {}

                    # 1. Visited link in Chrome
                    if next_ev.artifact_type == "BrowserHistory":
                        next_url = next_meta.get("url", "")
                        if domain and domain in next_url:
                            chain.append(next_ev)
                            visited.add(next_ev.id)
                            current_time = next_ev.timestamp
                            continue

                    # 2. File Download (apk or spoofed)
                    if next_ev.artifact_type == "File" and next_ev.timestamp - current_time < timedelta(minutes=15):
                        filename = next_meta.get("filename", "")
                        mime_type = next_meta.get("mime_type", "")
                        magic_bytes = next_meta.get("magic_bytes", "")
                        if "apk" in filename.lower() or "apk" in mime_type.lower() or "vnd.android.package-archive" in mime_type.lower() or magic_bytes == "504B0304":
                            chain.append(next_ev)
                            visited.add(next_ev.id)
                            current_time = next_ev.timestamp
                            continue

                    # 3. Application opening (banking or settings or installer)
                    if next_ev.artifact_type == "Application" and next_ev.timestamp - current_time < timedelta(minutes=15):
                        app_name = next_meta.get("app_name", "")
                        if "chrome" not in app_name.lower():
                            chain.append(next_ev)
                            visited.add(next_ev.id)
                            current_time = next_ev.timestamp
                            continue

                    # 4. OTP SMS
                    if next_ev.artifact_type == "SMS" and ("otp" in next_meta.get("message", "").lower() or "code" in next_meta.get("message", "").lower()):
                        chain.append(next_ev)
                        visited.add(next_ev.id)
                        current_time = next_ev.timestamp
                        continue

                if len(chain) > 1:
                    chains.append({
                        "type": "Phishing Sequence",
                        "confidence": 0.85 if len(chain) >= 3 else 0.6,
                        "events": chain,
                        "description": f"SMS phishing link received followed by matching browser activity and local operations within a {max_window.seconds // 60}-minute window."
                    })

            # Suspicious Contact Creation -> Call Sequence
            elif ev.artifact_type == "Contact":
                contact_num = meta.get("phone_number")
                contact_name = meta.get("name", "Unknown")
                if contact_num:
                    chain = [ev]
                    visited.add(ev.id)
                    current_time = ev.timestamp
                    
                    for j in range(i + 1, len(evidence_list)):
                        next_ev = evidence_list[j]
                        if next_ev.id in visited:
                            continue
                        if next_ev.timestamp - current_time > timedelta(hours=2):
                            break
                            
                        next_meta = json.loads(next_ev.metadata_json) if next_ev.metadata_json else {}
                        if next_ev.artifact_type == "Call" and next_meta.get("phone_number") == contact_num:
                            chain.append(next_ev)
                            visited.add(next_ev.id)
                            current_time = next_ev.timestamp
                            
                    if len(chain) > 1:
                        chains.append({
                            "type": "Call Infiltration",
                            "confidence": 0.75,
                            "events": chain,
                            "description": f"New contact '{contact_name}' created, followed by direct call log history within a short temporal window."
                        })

        # Step 2: Fallback temporal proximity groups
        # Group any remaining unvisited, non-GPS events occurring within 2 minutes of each other
        proximity_window = timedelta(minutes=2)
        current_chain = []
        
        for ev in evidence_list:
            if ev.id in visited or ev.artifact_type == "GPS":
                continue
            
            if not current_chain:
                current_chain.append(ev)
            else:
                last_ev = current_chain[-1]
                if ev.timestamp - last_ev.timestamp <= proximity_window:
                    current_chain.append(ev)
                else:
                    if len(current_chain) > 1:
                        for c_ev in current_chain:
                            visited.add(c_ev.id)
                        chains.append({
                            "type": "Temporal Proximity Cluster",
                            "confidence": 0.4,
                            "events": list(current_chain),
                            "description": "Sequence of different device activities occurring in close temporal proximity."
                        })
                    current_chain = [ev]
                    
        if len(current_chain) > 1:
            for c_ev in current_chain:
                visited.add(c_ev.id)
            chains.append({
                "type": "Temporal Proximity Cluster",
                "confidence": 0.4,
                "events": list(current_chain),
                "description": "Sequence of different device activities occurring in close temporal proximity."
            })

        return chains
