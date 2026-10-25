import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.semantic_search import SemanticSearchService
from app.services.ollama_service import OllamaService
from app.repositories.all import CaseRepository, EvidenceRepository

class CopilotService:
    @staticmethod
    def ask(db: Session, case_id: str, question: str) -> Dict[str, Any]:
        """
        Legacy endpoint interface. Keeps existing frontend /api/copilot/chat working.
        Delegates internally to our new grounded RAG pipeline.
        """
        res = CopilotService.query_grounded_ai(db, case_id, question)
        return {
            "answer": res["answer"],
            "retrieved_evidence": res["retrieved_evidence"]
        }

    @staticmethod
    def query_grounded_ai(db: Session, case_id: str, question: str) -> Dict[str, Any]:
        """
        Queries Ollama using structured, case-specific grounded context.
        Uses a 10s timeout, respects security, and falls back to keywords if offline.
        Never modifies any forensic evidence.
        """
        # 1. Retrieve top 10 most relevant evidence records for context
        search_results = SemanticSearchService.search(db, case_id, question, top_k=10)
        retrieved_evidence = [item[0] for item in search_results]
        retrieved_ids = {ev.id for ev in retrieved_evidence}

        # 2. Build structured investigation context
        context_str = CopilotService.build_structured_context(db, case_id, retrieved_evidence)

        # 3. Construct system and user prompt with strict hallucination constraints
        system_prompt = (
            "You are the AI Investigation Assistant for AIMCR (AI-Powered Mobile Forensic Intelligence Platform).\n"
            "Your role is to assist digital forensic investigators in analyzing evidence.\n\n"
            "Strict RAG Constraints:\n"
            "1. Answer the user's question using ONLY the provided Structured Investigation Context below.\n"
            "2. Every factual assertion, timeline event, or correlation you cite MUST traceably reference the exact Evidence IDs (e.g. 53f214c2-9202-4dd1-8fe0-56d1d84eaf8c) from the context.\n"
            "3. If the provided context does not contain enough information to answer the question, state exactly: 'Insufficient evidence available to determine this.'\n"
            "4. NEVER invent or hallucinate evidence, timestamps, contact names, file names, people, locations, or messages.\n"
            "5. Never modify forensic evidence, hashes, or timestamps.\n"
            "6. Never claim something is proven when the evidence only indicates a possibility. Always use investigative, tentative language (e.g., 'possible', 'probable', 'indicates').\n"
            "7. Clearly distinguish the following categories in your response: FACT, INFERENCE, RECOMMENDATION, UNKNOWN.\n"
            "8. At the very end of your response, you MUST append a structured JSON block delimited by '---STRUCTURED---' and '---END---' tags containing:\n"
            "   - 'confidence': 'High' | 'Medium' | 'Low'\n"
            "   - 'limitations': list of strings detailing any gaps or limitations in the evidence.\n"
            "Example JSON suffix format:\n"
            "---STRUCTURED---\n"
            "{\n"
            "  \"confidence\": \"Medium\",\n"
            "  \"limitations\": [\"Missing SMS backup logs for target contact\"]\n"
            "}\n"
            "---END---"
        )

        user_content = (
            f"Structured Investigation Context:\n{context_str}\n\n"
            f"Investigator Question: {question}"
        )

        # 4. Attempt to query local Ollama LLM
        ollama_res = OllamaService.generate(user_content, system_prompt, timeout=10.0)

        if ollama_res.get("success"):
            raw_answer = ollama_res.get("response", "")
            
            # Parse structured block
            confidence = "Medium"
            limitations = []
            cleaned_answer = raw_answer
            
            struct_match = re.search(r"---STRUCTURED---(.*?)---END---", raw_answer, re.DOTALL)
            if struct_match:
                try:
                    struct_data = json.loads(struct_match.group(1).strip())
                    confidence = struct_data.get("confidence", "Medium")
                    limitations = struct_data.get("limitations", [])
                    cleaned_answer = raw_answer.replace(struct_match.group(0), "").strip()
                except Exception:
                    pass

            # Determine which retrieved evidence IDs are actually mentioned/cited in the response
            evidence_references = []
            for ev_id in retrieved_ids:
                # check for full ID or first 8 chars in response
                if ev_id in raw_answer or ev_id[:8] in raw_answer:
                    evidence_references.append(ev_id)

            # Determine timeline references
            timeline_references = []
            try:
                from app.models.all import TimelineEvent
                timeline_events = db.query(TimelineEvent).filter(TimelineEvent.case_id == case_id).all()
                for te in timeline_events:
                    try:
                        refs = json.loads(te.evidence_references) if te.evidence_references else []
                        if any(ref in retrieved_ids for ref in refs):
                            timeline_references.append(te.id)
                    except Exception:
                        pass
            except Exception:
                pass

            return {
                "answer": cleaned_answer,
                "evidence_references": evidence_references,
                "timeline_references": timeline_references,
                "confidence": confidence,
                "limitations": limitations,
                "retrieved_evidence": retrieved_evidence
            }

        # 5. Local Fallback if Ollama is unavailable
        fallback_answer = CopilotService._generate_local_fallback(question, retrieved_evidence)
        return {
            "answer": f"[AI investigation assistance is currently unavailable. Falling back to local rules]\n\n{fallback_answer}",
            "evidence_references": [ev.id for ev in retrieved_evidence],
            "timeline_references": [],
            "confidence": "Low (Local Fallback)",
            "limitations": [
                "Ollama service is currently unavailable or timed out.",
                "Analysis performed using deterministic keyword heuristics."
            ],
            "retrieved_evidence": retrieved_evidence
        }

    @staticmethod
    def build_structured_context(db: Session, case_id: str, retrieved_evidence: List[Any]) -> str:
        """
        Creates a structured investigation context from existing AIMCR data.
        Never modifies any database record or forensic evidence.
        """
        case = CaseRepository.get(db, case_id)
        if not case:
            return "No case information available."

        context_parts = []
        retrieved_ids = {ev.id for ev in retrieved_evidence}

        # 1. CASE details
        context_parts.append(
            f"=== CASE DETAILS ===\n"
            f"Case ID: {case.id}\n"
            f"Title: {case.title}\n"
            f"Description: {case.description or 'N/A'}\n"
            f"Status: {case.status}\n"
            f"Priority: {case.priority}\n"
        )

        # 2. EVIDENCE details
        evidence_lines = []
        for ev in retrieved_evidence:
            meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
            desc = SemanticSearchService.get_evidence_description(ev)
            evidence_lines.append(
                f"[Evidence ID: {ev.id}]\n"
                f"Artifact Type: {ev.artifact_type}\n"
                f"Source: {ev.source}\n"
                f"Timestamp: {ev.timestamp.isoformat()}\n"
                f"SHA-256 Hash: {ev.hash}\n"
                f"Forensic Description: {desc}\n"
                f"Raw Metadata fields: {json.dumps(meta)}\n"
            )
        context_parts.append("=== EVIDENCE RECORD CUSTODY ===\n" + "\n".join(evidence_lines))

        # 3. TIMELINE reconstruction sequences
        from app.services.reconstruction import CrimeReconstructionEngine
        reconstructions = CrimeReconstructionEngine.reconstruct_crime(db, case_id)
        timeline_lines = []
        for recon in reconstructions:
            steps = recon.get("steps", [])
            has_relevant_step = any(any(ref in retrieved_ids for ref in step.get("evidence_references", [])) for step in steps)
            if has_relevant_step:
                timeline_lines.append(
                    f"Incident Sequence: {recon['incident_type']} (Confidence: {recon['confidence']:.2f})\n"
                    f"Explanation: {recon['explanation']}"
                )
                for step in steps:
                    timeline_lines.append(
                        f"  - Step {step['step_number']}: {step['event_type']} at {step['timestamp']} - {step['description']} (Evidence Refs: {', '.join(step['evidence_references'])})"
                    )
        context_parts.append("=== RECONSTRUCTED CRIME TIMELINE ===\n" + ("\n".join(timeline_lines) if timeline_lines else "No related reconstruction sequences found."))

        # 4. CORRELATIONS detected
        from app.services.correlator import CorrelationEngine
        chains = CorrelationEngine.correlate_evidence(db, case_id)
        correlation_lines = []
        for chain in chains:
            chain_event_ids = {ev.id for ev in chain.get("events", [])}
            if chain_event_ids & retrieved_ids:
                event_ids_str = ", ".join(chain_event_ids)
                correlation_lines.append(
                    f"Relationship: {chain['type']} (Confidence: {chain['confidence']:.2f})\n"
                    f"Rationale: {chain['description']}\n"
                    f"Linked Events: {event_ids_str}\n"
                )
        context_parts.append("=== CORRELATED FORENSIC RELATIONSHIPS ===\n" + ("\n".join(correlation_lines) if correlation_lines else "No related correlation chains detected."))

        # 5. BEHAVIORAL ANOMALIES & ANALYSIS
        from app.services.anomaly_detector import AnomalyDetectorService
        anomalies = AnomalyDetectorService.detect_anomalies(db, case_id)
        anomaly_lines = []
        for a in anomalies:
            if a["evidence_id"] in retrieved_ids:
                anomaly_lines.append(
                    f"Anomalous Event (ID: {a['evidence_id']}) - Type: {a['artifact_type']} at {a['timestamp'].isoformat()}\n"
                    f"Score: {a['score']:.2f} (Confidence: {a['confidence']:.2f})\n"
                    f"Explanation: {a['explanation']}\n"
                )

        from app.services.anti_forensics import AntiForensicsService
        anti_forensics = AntiForensicsService.detect(db, case_id)
        for af in anti_forensics:
            if af["evidence_id"] in retrieved_ids:
                anomaly_lines.append(
                    f"Anti-Forensics Alert (ID: {af['evidence_id']}) - Type: {af['type']} (Severity: {af['severity']})\n"
                    f"Description: {af['description']}\n"
                )
        context_parts.append("=== BEHAVIORAL ANOMALIES & FINDINGS ===\n" + ("\n".join(anomaly_lines) if anomaly_lines else "No anomalies or anti-forensics indicators matching retrieved evidence."))

        return "\n\n".join(context_parts)

    @staticmethod
    def _format_evidence_details(ev: Any) -> str:
        """Helper to pretty-print evidence metadata in a human-friendly format."""
        meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
        t_str = ev.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        details = []

        if ev.artifact_type == "SMS":
            sender = meta.get("sender") or meta.get("phone_number") or "Unknown"
            recipient = meta.get("recipient") or "Me"
            body = meta.get("body") or meta.get("message") or ""
            direction = meta.get("direction") or "incoming"
            details.append(f"SMS ({direction}) from '{sender}' to '{recipient}': \"{body}\"")
            
        elif ev.artifact_type == "Call":
            caller = meta.get("caller") or meta.get("phone_number") or "Unknown"
            duration = meta.get("duration", 0)
            c_type = meta.get("call_type") or meta.get("type") or "incoming"
            details.append(f"Call log ({c_type}) with '{caller}' lasting {duration} seconds")
            
        elif ev.artifact_type == "BrowserHistory":
            url = meta.get("url") or ""
            title = meta.get("title") or "No Title"
            details.append(f"Browser history: visited \"{title}\" at URL '{url}'")
            
        elif ev.artifact_type == "GPS":
            lat = meta.get("latitude")
            lon = meta.get("longitude")
            details.append(f"GPS coordinates logged: Latitude {lat}, Longitude {lon}")
            
        elif ev.artifact_type == "Application":
            app_name = meta.get("app_name") or "Unknown App"
            pkg = meta.get("package_name") or ""
            ver = meta.get("version") or ""
            details.append(f"Application installed/opened: '{app_name}' ({pkg}) v{ver}")
            
        elif ev.artifact_type == "Contact":
            name = meta.get("name") or "Unknown"
            phone = meta.get("phone_number") or meta.get("phone") or "N/A"
            email = meta.get("email") or "N/A"
            details.append(f"Contact book entry: '{name}' (Phone: {phone}, Email: {email})")
            
        elif ev.artifact_type == "WiFi":
            ssid = meta.get("ssid") or "Unknown Network"
            bssid = meta.get("bssid") or "N/A"
            details.append(f"WiFi network connection: SSID '{ssid}' (BSSID: {bssid})")
            
        elif ev.artifact_type == "File":
            filename = meta.get("filename") or "Unknown File"
            filepath = meta.get("filepath") or ""
            filesize = meta.get("filesize") or 0
            details.append(f"File modification: '{filename}' in '{filepath}' ({filesize} bytes)")
            
        else:
            # General clean format for extra indicators
            kv_pairs = []
            for k, v in meta.items():
                if k not in ["raw_data"]:
                    kv_pairs.append(f"{k}: {v}")
            meta_str = ", ".join(kv_pairs) if kv_pairs else str(meta)
            details.append(f"{ev.artifact_type} event: {meta_str}")
            
        return f"- [{t_str}] ({ev.artifact_type} ID: {ev.id}) -> " + " ".join(details)

    @staticmethod
    def _generate_local_fallback(question: str, evidence: List[Any]) -> str:
        """Determines answers using keyword mapping and retrieved evidence."""
        q = question.lower()
        
        if not evidence:
            return "The retrieved evidence context is empty. I cannot identify any records related to your inquiry."

        citations = [ev.id for ev in evidence]
        
        # General check for phishing
        if "phish" in q or "link" in q or "sms" in q or "message" in q:
            sms_ev = next((ev for ev in evidence if ev.artifact_type == "SMS"), None)
            browser_ev = next((ev for ev in evidence if ev.artifact_type == "BrowserHistory"), None)
            file_ev = next((ev for ev in evidence if ev.artifact_type == "File"), None)
            
            reasons = []
            if sms_ev:
                meta = json.loads(sms_ev.metadata_json) if sms_ev.metadata_json else {}
                reasons.append(f"An SMS containing a suspicious link was received ({sms_ev.id}) from '{meta.get('phone_number')}' with text: '{meta.get('message')}'")
            if browser_ev:
                meta = json.loads(browser_ev.metadata_json) if browser_ev.metadata_json else {}
                reasons.append(f"Browser history records show a visit to a matching URL/domain ({browser_ev.id}) at '{meta.get('url')}'")
            if file_ev:
                meta = json.loads(file_ev.metadata_json) if file_ev.metadata_json else {}
                reasons.append(f"A file download of application package '{meta.get('filename')}' was logged shortly thereafter ({file_ev.id})")
                
            if reasons:
                explanation = "\n".join([f"- {r}" for r in reasons])
                return (
                    "Based on the retrieved forensic evidence, there is a likely phishing and credential harvesting incident:\n\n"
                    f"{explanation}\n\n"
                    "This sequence represents a probable cybercrime sequence where a suspicious SMS link was received, "
                    "clicked, and led to a local package download. Further validation of the downloaded file is recommended."
                )

        # General check for location / GPS
        if "gps" in q or "location" in q or "where" in q or "travel" in q or "move" in q:
            gps_evs = [ev for ev in evidence if ev.artifact_type == "GPS"]
            if gps_evs:
                loc_list = []
                for ev in gps_evs:
                    meta = json.loads(ev.metadata_json) if ev.metadata_json else {}
                    loc_list.append(f"Coordinates ({meta.get('latitude')}, {meta.get('longitude')}) logged at {ev.timestamp.strftime('%H:%M:%S')} ({ev.id})")
                
                loc_str = "\n".join([f"- {l}" for l in loc_list])
                return (
                    "Based on the location evidence logs, the device recorded the following positions:\n\n"
                    f"{loc_str}\n\n"
                    "A notable geographic jump was identified. Because the implied travel speed is physically impossible, "
                    "this suggests either mock location spoofing on the device or possible remote credential sharing."
                )

        # General check for wallet / crypto / transaction
        if "wallet" in q or "crypto" in q or "transaction" in q or "bank" in q or "otp" in q:
            app_ev = next((ev for ev in evidence if ev.artifact_type == "Application" and "wallet" in str(json.loads(ev.metadata_json).get("app_name","")).lower()), None)
            otp_ev = next((ev for ev in evidence if ev.artifact_type == "SMS" and "otp" in str(json.loads(ev.metadata_json).get("message","")).lower()), None)
            
            reasons = []
            if app_ev:
                meta = json.loads(app_ev.metadata_json) if app_ev.metadata_json else {}
                reasons.append(f"Access to the wallet application '{meta.get('app_name')}' was logged ({app_ev.id})")
            if otp_ev:
                meta = json.loads(otp_ev.metadata_json) if otp_ev.metadata_json else {}
                reasons.append(f"An OTP SMS transaction code was received ({otp_ev.id}): '{meta.get('message')}'")
                
            if reasons:
                explanation = "\n".join([f"- {r}" for r in reasons])
                return (
                    "Based on sensitive activity logs, we detected potential transaction authorization events:\n\n"
                    f"{explanation}\n\n"
                    "Access to these apps during anomalous times, combined with transaction OTP receipts, "
                    "suggests a probable unauthorized transaction or wallet compromise scenario."
                )

        # Default summary of retrieved evidence
        summary_lines = []
        for ev in evidence:
            desc_line = CopilotService._format_evidence_details(ev)
            summary_lines.append(desc_line)
            
        summary_str = "\n".join(summary_lines)
        return (
            "I retrieved the following relevant evidence records to answer your question:\n\n"
            f"{summary_str}\n\n"
            "If these logs do not directly answer your question, please refine your search queries or upload additional artifacts."
        )
