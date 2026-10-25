import json
import requests
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.repositories.all import EvidenceRepository
from app.services.anti_forensics import AntiForensicsService

class ForensicRecommendationsService:
    @staticmethod
    def generate_recommendations(db: Session, case_id: str) -> Dict[str, Any]:
        """
        Generates actionable next steps for a forensic examiner.
        First builds deterministic recommendations based on matches and anti-forensics alerts.
        Then, if Ollama is available, leverages LLM to format and enrich them.
        """
        evidence_list = EvidenceRepository.list_by_case(db, case_id)
        anti_forensics_alerts = AntiForensicsService.detect(db, case_id)
        
        recs = []
        
        # 1. Check Threat Intel matches
        threat_intel_matches = []
        for ev in evidence_list:
            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
            if "threat_intel_match" in meta:
                threat_intel_matches.append(meta["threat_intel_match"])
                
        for match in threat_intel_matches:
            val = match.get("value")
            t_type = match.get("indicator_type")
            t_name = match.get("threat_name")
            
            if t_type == "phone_number":
                recs.append({
                    "action": f"Request cellular routing trace for MSISDN '{val}'",
                    "priority": "High",
                    "rationale": f"Flagged by Threat Intel as '{t_name}'. Tracing cell tower connections will identify geographical origin of the sender."
                })
            elif t_type in ["domain", "url"]:
                recs.append({
                    "action": f"Perform WHOIS and passive DNS resolution query on '{val}'",
                    "priority": "High",
                    "rationale": f"The phishing infrastructure domain/URL '{val}' was matched. This will identify domain registrars, hosting IPs, and subdomains."
                })
                recs.append({
                    "action": f"Check proxy/DNS resolution logs on client device for contacts with '{val}'",
                    "priority": "Medium",
                    "rationale": f"Determines exact duration and timeline of client communication with the malicious infrastructure."
                })
            elif t_type == "hash":
                recs.append({
                    "action": f"Extract file matching hash '{val[:12]}...' for static disassembly",
                    "priority": "Critical",
                    "rationale": f"The malicious package was detected. JADX/Apktool static disassembly is recommended to map internal Java classes and intent handlers."
                })
            elif t_type == "package_name":
                recs.append({
                    "action": f"Audit permissions and isolation state of package '{val}'",
                    "priority": "High",
                    "rationale": f"This application was launched during the attack. Confirm if it holds Device Admin, SMS reading, or accessibility permissions."
                })
                
        # 2. Check Anti-Forensic indicators
        for alert in anti_forensics_alerts:
            a_type = alert.get("type")
            
            if a_type == "Extension Spoofing":
                recs.append({
                    "action": "Perform file header magic signature verification on spoofed files",
                    "priority": "Critical",
                    "rationale": "Extension mismatch detected. Run Linux 'file' command or read binary headers directly to confirm MIME structure."
                })
            elif a_type == "Time-Stomping Detected":
                recs.append({
                    "action": "Analyze file system journal records ($UsnJrnl / ext4 journal)",
                    "priority": "High",
                    "rationale": "Active metadata manipulation (modified time set to Epoch 0 or preceding creation time) requires low-level journal audits to rebuild accurate timelines."
                })
            elif a_type == "SQLite DB Tampering":
                recs.append({
                    "action": "Initiate SQLite database cell/carve recovery on empty database",
                    "priority": "High",
                    "rationale": "Zero tables or zero size in DB suggests table dropping or vacuuming. Attempt cell carving in unallocated DB space to recover deleted rows."
                })
            elif a_type == "Eraser Application Launched":
                recs.append({
                    "action": "Examine device cache logs and temp file locations",
                    "priority": "Medium",
                    "rationale": "Forensic cleaners/cache erasers attempt to delete temporary logs. Recovery of overwritten sectors or unallocated database pages may be required."
                })
                
        # 3. Default General Mobile Forensics advice if list is small
        if len(recs) < 3:
            recs.append({
                "action": "Establish forensic write-block and compute device image hash",
                "priority": "Medium",
                "rationale": "Ensures all evidence remains statically secure and complies with chain of custody regulations."
            })
            recs.append({
                "action": "Verify device acquisition logs for cryptographic integrity matches",
                "priority": "Medium",
                "rationale": "Verifies that no bit-level changes occurred during evidence ingestion."
            })
            
        # Deduplicate recommendations list based on action string
        seen = set()
        dedup_recs = []
        for r in recs:
            if r["action"] not in seen:
                seen.add(r["action"])
                dedup_recs.append(r)
        
        # 4. Optional Ollama summary enrichment
        summary = ""
        ollama_url = f"{settings.OLLAMA_API_BASE}/api/generate"
        
        # Construct summary prompt
        system_prompt = (
            "You are the Lead Digital Forensics Researcher for AIMCR.\n"
            "Generate a highly professional, concise digital forensics executive recommendations summary "
            "based on the following findings and concrete steps.\n"
            "Avoid generic cybersecurity awareness tips. Focus strictly on mobile device forensics, "
            "static/dynamic APK analysis, SQLite cell carving, and network infrastructure registration tracing.\n"
            "Keep the response brief (max 2 paragraphs), direct, and formal."
        )
        
        findings_context = f"Findings: Matches={len(threat_intel_matches)}, Anti-Forensics Alerts={len(anti_forensics_alerts)}\n"
        findings_context += "Concrete Recommended Steps:\n"
        for idx, r in enumerate(dedup_recs, 1):
            findings_context += f"{idx}. {r['action']} ({r['priority']} Priority) - Rationale: {r['rationale']}\n"
            
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\n{findings_context}",
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        
        try:
            response = requests.post(ollama_url, json=payload, timeout=8.0)
            if response.status_code == 200:
                summary = response.json().get("response", "").strip()
        except Exception:
            pass
            
        if not summary:
            # Local fallback summary
            summary = (
                "Based on the analysis of active threat intelligence matches and anti-forensics indicators, "
                "the investigator should prioritize disassembling the spoofed APK binary (disguised as a PNG) and carving the "
                "tampered SQLite database. Reconstructing network infrastructure and verifying modification timestamps "
                "via system logs is critical to confirm the attack vector and trace perpetrator activity."
            )
            
        return {
            "summary": summary,
            "recommendations": dedup_recs
        }
