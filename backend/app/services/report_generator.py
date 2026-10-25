import os
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.models.all import Case, Report
from app.repositories.all import CaseRepository, EvidenceRepository, AuditLogRepository
from app.services.anomaly_detector import AnomalyDetectorService
from app.services.graph_engine import GraphEngineService
from app.services.reconstruction import CrimeReconstructionEngine

class NumberedCanvas(canvas.Canvas):
    """Custom canvas to draw running headers, footers and 'Page X of Y' page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header (Skip on first page)
        if self._pageNumber > 1:
            self.drawString(54, 750, "AIMCR — Forensic Intelligence Report")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
            
        # Footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 50, 558, 50)
        
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 35, page_text)
        self.drawString(54, 35, "CONFIDENTIAL — Authorized Forensic Investigation Use Only")
        self.restoreState()

class ReportGeneratorService:
    @staticmethod
    def generate_report(db: Session, case_id: str) -> str:
        case = CaseRepository.get(db, case_id)
        if not case:
            raise ValueError("Case not found")

        # 1. Retrieve all analysis data
        evidence = EvidenceRepository.list_by_case(db, case_id)
        anomalies = AnomalyDetectorService.detect_anomalies(db, case_id)
        graph = GraphEngineService.build_communication_graph(db, case_id)
        reconstructions = CrimeReconstructionEngine.reconstruct_crime(db, case_id)
        audit_logs = AuditLogRepository.list_all(db, limit=20)

        # Create reports directory if it doesn't exist (env-configurable)
        reports_dir = settings.REPORTS_DIR
        os.makedirs(reports_dir, exist_ok=True)
        
        report_id = str(uuid.uuid4())
        filepath = os.path.join(reports_dir, f"{report_id}.pdf")

        # Setup PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        
        # Define customized Paragraph Styles
        styles.add(ParagraphStyle(
            name="CoverTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=32,
            textColor=colors.HexColor("#1A202C"),
            spaceAfter=15
        ))
        
        styles.add(ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=40
        ))
        
        styles.add(ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=18,
            spaceAfter=10,
            keepWithNext=True
        ))

        styles.add(ParagraphStyle(
            name="SubSectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2D3748"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        ))

        styles.add(ParagraphStyle(
            name="BodyTextDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=8
        ))

        styles.add(ParagraphStyle(
            name="BodyTextBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1A202C"),
            spaceAfter=8
        ))

        styles.add(ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2D3748")
        ))

        styles.add(ParagraphStyle(
            name="TableCellHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.white
        ))

        story = []

        # --- COVER PAGE ---
        story.append(Spacer(1, 40))
        story.append(Paragraph("AIMCR FORENSIC REPORT", styles["CoverTitle"]))
        story.append(Paragraph("AI-Powered Mobile Forensic Intelligence Platform for Autonomous Crime Reconstruction", styles["CoverSubtitle"]))
        story.append(Spacer(1, 20))
        
        # Compute complexity & anti-forensics details
        from app.services.risk_scorer import ForensicComplexityService
        from app.services.anti_forensics import AntiForensicsService
        from app.services.recommendations import ForensicRecommendationsService

        complexity = ForensicComplexityService.calculate_complexity(db, case_id)
        anti_forensics = AntiForensicsService.detect(db, case_id)
        recs = ForensicRecommendationsService.generate_recommendations(db, case_id)

        # Case Details Box
        case_data = [
            [Paragraph("<b>Case Reference:</b>", styles["BodyTextDark"]), Paragraph(case.title, styles["BodyTextDark"])],
            [Paragraph("<b>Case Status:</b>", styles["BodyTextDark"]), Paragraph(case.status, styles["BodyTextDark"])],
            [Paragraph("<b>Date Generated:</b>", styles["BodyTextDark"]), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles["BodyTextDark"])],
            [Paragraph("<b>Assigned Investigator:</b>", styles["BodyTextDark"]), Paragraph(case.investigator.name if case.investigator else "Unassigned", styles["BodyTextDark"])],
            [Paragraph("<b>Evidence Count:</b>", styles["BodyTextDark"]), Paragraph(f"{len(evidence)} artifacts ingested", styles["BodyTextDark"])],
            [Paragraph("<b>Forensic Complexity Index:</b>", styles["BodyTextDark"]), Paragraph(f"{complexity['score']}/100 ({complexity['rating']})", styles["BodyTextDark"])],
        ]
        
        case_table = Table(case_data, colWidths=[150, 300])
        case_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 12),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(case_table)
        story.append(Spacer(1, 40))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
        story.append(Paragraph(
            "This document compiles explainable investigative findings extracted from mobile device artifacts using the "
            "Autonomous Crime Reconstruction and Behavioral Profiling engines. Every finding detailed within "
            "this report is traceably backed by a corresponding SHA-256 hashed forensic artifact, maintaining full chain "
            "of custody. The contents represent investigative directions and indicators of probability rather than "
            "definitive judicial outcomes.",
            styles["BodyTextDark"]
        ))
        
        story.append(PageBreak())

        # --- SECTION 1: CRIME RECONSTRUCTION ---
        story.append(Paragraph("PART I: FORENSIC FACTS (DETERMINISTIC ANALYSIS)", styles["SectionHeading"]))
        story.append(Paragraph(
            "The following sections compile deterministic logs, anomalies, anti-forensics alerts, and modular graphs "
            "directly extracted from device artifacts. All forensic findings are backed by SHA-256 integrity hashes.",
            styles["BodyTextDark"]
        ))
        story.append(Spacer(1, 10))
        story.append(Paragraph("1. Incident Reconstruction", styles["SubSectionHeading"]))
        if not reconstructions:
            story.append(Paragraph("No structured cybercrime sequences were reconstructed by the engine.", styles["BodyTextDark"]))
        else:
            for r in reconstructions:
                story.append(Paragraph(f"Incident Class: {r['incident_type']}", styles["SubSectionHeading"]))
                story.append(Paragraph(f"<b>Reconstruction Explanation:</b> {r['explanation']}", styles["BodyTextDark"]))
                story.append(Paragraph(f"<b>Reconstruction Confidence:</b> {int(r['confidence'] * 100)}%", styles["BodyTextDark"]))
                story.append(Spacer(1, 10))

                # Step Table
                step_data = [[
                    Paragraph("Step", styles["TableCellHeader"]),
                    Paragraph("Type", styles["TableCellHeader"]),
                    Paragraph("Description", styles["TableCellHeader"]),
                    Paragraph("Timestamp", styles["TableCellHeader"]),
                    Paragraph("Evidence Refs", styles["TableCellHeader"])
                ]]
                for step in r["steps"]:
                    step_data.append([
                        Paragraph(str(step["step_number"]), styles["TableCell"]),
                        Paragraph(step["event_type"], styles["TableCell"]),
                        Paragraph(step["description"], styles["TableCell"]),
                        Paragraph(step["timestamp"][:19].replace("T", " "), styles["TableCell"]),
                        Paragraph(", ".join(step["evidence_references"]), styles["TableCell"])
                    ])
                
                step_table = Table(step_data, colWidths=[40, 60, 210, 110, 80])
                step_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('PADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(step_table)
                story.append(Spacer(1, 20))

        story.append(Spacer(1, 15))

        # --- SECTION 2: BEHAVIORAL ANOMALIES ---
        story.append(Paragraph("2. Behavioral Anomaly Log", styles["SectionHeading"]))
        story.append(Paragraph(
            "The Isolation Forest engine analyzed the user's historical feature vectors (active hours, GPS coordinates, application categories, file extensions) and highlighted the following deviations from baseline behavior:",
            styles["BodyTextDark"]
        ))
        
        if not anomalies:
            story.append(Paragraph("No behavioral deviations were flagged by the anomaly detector.", styles["BodyTextDark"]))
        else:
            anomaly_data = [[
                Paragraph("Timestamp", styles["TableCellHeader"]),
                Paragraph("Type", styles["TableCellHeader"]),
                Paragraph("Score", styles["TableCellHeader"]),
                Paragraph("Anomaly Explanation / Context", styles["TableCellHeader"]),
                Paragraph("Ref", styles["TableCellHeader"])
            ]]
            for a in anomalies:
                anomaly_data.append([
                    Paragraph(a["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), styles["TableCell"]),
                    Paragraph(a["artifact_type"], styles["TableCell"]),
                    Paragraph(f"{a['score']:.2f}", styles["TableCell"]),
                    Paragraph(a["explanation"], styles["TableCell"]),
                    Paragraph(a["evidence_id"][:8], styles["TableCell"])
                ])
            
            anomaly_table = Table(anomaly_data, colWidths=[100, 65, 45, 230, 60])
            anomaly_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4A5568")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(anomaly_table)

        story.append(Spacer(1, 15))
        # --- SECTION 2a: ANTI-FORENSICS AND TAMPERING ---
        story.append(Paragraph("2a. Anti-Forensics & Tampering Log", styles["SectionHeading"]))
        story.append(Paragraph(
            "Heuristic scanners inspected the integrity of the device artifacts to find evidence of active concealment, extension spoofing, file system timestamp manipulation, or database tampering:",
            styles["BodyTextDark"]
        ))
        if not anti_forensics:
            story.append(Paragraph("No active anti-forensics attempts or database anomalies were flagged.", styles["BodyTextDark"]))
        else:
            af_data = [[
                Paragraph("Anomaly Type", styles["TableCellHeader"]),
                Paragraph("Severity", styles["TableCellHeader"]),
                Paragraph("Description", styles["TableCellHeader"]),
                Paragraph("Evidence Ref", styles["TableCellHeader"])
            ]]
            for af in anti_forensics:
                af_data.append([
                    Paragraph(af["type"], styles["TableCell"]),
                    Paragraph(af["severity"], styles["TableCell"]),
                    Paragraph(af["description"], styles["TableCell"]),
                    Paragraph(af["evidence_id"][:8] + "...", styles["TableCell"])
                ])
            af_table = Table(af_data, colWidths=[120, 60, 240, 80])
            af_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7B341E")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(af_table)

        story.append(PageBreak())

        # --- SECTION 3: COMMUNICATION GRAPH ---
        story.append(Paragraph("3. Relationship Network & Priority Entities", styles["SectionHeading"]))
        story.append(Paragraph(
            "The communication graph maps contacts, browser domains, and apps into connected modular communities. Nodes are assigned an Investigative Priority score using degree and betweenness centralities.",
            styles["BodyTextDark"]
        ))
        
        if not graph or not graph.get("nodes"):
            story.append(Paragraph("Insufficient relationship data to generate communication graph metrics.", styles["BodyTextDark"]))
        else:
            # Sort nodes by priority score descending
            sorted_nodes = sorted(graph["nodes"], key=lambda x: x["priority_score"], reverse=True)
            
            story.append(Paragraph("Priority Investigation Targets", styles["SubSectionHeading"]))
            
            priority_data = [[
                Paragraph("Entity Identifier", styles["TableCellHeader"]),
                Paragraph("Node Class", styles["TableCellHeader"]),
                Paragraph("Investigative Priority Score", styles["TableCellHeader"]),
                Paragraph("Action Needed", styles["TableCellHeader"])
            ]]
            for node in sorted_nodes[:6]:
                action = "Immediate Forensics Review" if node["priority_score"] > 80 else "Monitor & Validate"
                priority_data.append([
                    Paragraph(node["label"], styles["TableCell"]),
                    Paragraph(node["type"], styles["TableCell"]),
                    Paragraph(f"{node['priority_score']}/100", styles["TableCell"]),
                    Paragraph(action, styles["TableCell"])
                ])
                
            priority_table = Table(priority_data, colWidths=[150, 100, 110, 140])
            priority_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(priority_table)

        story.append(Spacer(1, 15))
        # --- SECTION 3a: FORENSIC INVESTIGATION RECOMMENDATIONS ---
        story.append(Paragraph("3a. Forensic Investigation Recommendations", styles["SectionHeading"]))
        story.append(Paragraph(
            f"<b>AI/Deterministic Recommendations Summary:</b> {recs['summary']}",
            styles["BodyTextDark"]
        ))
        story.append(Spacer(1, 10))

        rec_data = [[
            Paragraph("Recommended Actions", styles["TableCellHeader"]),
            Paragraph("Priority", styles["TableCellHeader"]),
            Paragraph("Forensic Rationale / Next Steps", styles["TableCellHeader"])
        ]]
        for r in recs["recommendations"]:
            rec_data.append([
                Paragraph(r["action"], styles["TableCell"]),
                Paragraph(r["priority"], styles["TableCell"]),
                Paragraph(r["rationale"], styles["TableCell"])
            ])
        rec_table = Table(rec_data, colWidths=[180, 60, 260])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C7A7B")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 20))

        # --- SECTION 4: EVIDENCE INTEGRITY INDEX ---
        story.append(Paragraph("4. Evidence Integrity Index (Chain of Custody)", styles["SectionHeading"]))
        story.append(Paragraph(
            "Every artifact imported into the platform is indexed below with its original acquisition timestamp and a SHA-256 integrity hash to ensure transparency and auditability.",
            styles["BodyTextDark"]
        ))
        
        ev_data = [[
            Paragraph("Evidence ID", styles["TableCellHeader"]),
            Paragraph("Timestamp", styles["TableCellHeader"]),
            Paragraph("Type", styles["TableCellHeader"]),
            Paragraph("Source File", styles["TableCellHeader"]),
            Paragraph("SHA-256 Hash Signature", styles["TableCellHeader"])
        ]]
        for ev in evidence[:25]:  # limit list in PDF for neatness
            ev_data.append([
                Paragraph(ev.id[:8] + "...", styles["TableCell"]),
                Paragraph(ev.timestamp.strftime("%Y-%m-%d %H:%M:%S"), styles["TableCell"]),
                Paragraph(ev.artifact_type, styles["TableCell"]),
                Paragraph(ev.source, styles["TableCell"]),
                Paragraph(ev.hash[:16] + "...", styles["TableCell"])
            ])
            
        ev_table = Table(ev_data, colWidths=[70, 110, 70, 110, 140])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2D3748")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(ev_table)
        if len(evidence) > 25:
            story.append(Paragraph(f"<i>* Showing 25 of {len(evidence)} total evidence records. Full trace available in database.</i>", styles["BodyTextDark"]))

        # --- PART II: AI-ASSISTED INTERPRETATION ---
        story.append(PageBreak())
        story.append(Paragraph("PART II: AI-ASSISTED INTERPRETATION (NON-DETERMINISTIC SUMMARY)", styles["SectionHeading"]))
        story.append(Paragraph(
            "<b>Important Notice:</b> The content in this section is automatically generated by a local, on-premise Large Language Model "
            "using grounded context from parsed device evidence. It is intended for interpretation and intelligence-guided search assistance. "
            "This summary is non-deterministic and must be independently verified by a human forensic examiner. It does not replace original forensic facts.",
            styles["BodyTextDark"]
        ))
        story.append(Spacer(1, 10))
        
        # Generate AI-Assisted Interpretation and Summary
        ai_summary = ""
        ai_confidence = "Low (Fallback)"
        ai_limitations = []
        
        try:
            from app.services.copilot import CopilotService
            prompt = (
                "Generate a professional, cohesive digital forensics investigation summary for this case. "
                "The summary MUST cover the following sections in a highly structured manner:\n"
                "1. Case Overview\n"
                "2. Key Evidence & Hashing\n"
                "3. Significant Timeline Events\n"
                "4. Correlated Evidence Chains\n"
                "5. Suspicious Activities & Anomaly Assessments\n"
                "6. AI Observations\n"
                "7. Recommended Next Investigation Steps\n"
                "8. Evidence Limitations & Gaps\n"
                "Ensure your observations are clearly distinguished from raw deterministic facts."
            )
            ai_res = CopilotService.query_grounded_ai(db, case_id, prompt)
            ai_summary = ai_res.get("answer", "")
            ai_confidence = ai_res.get("confidence", "Medium")
            ai_limitations = ai_res.get("limitations", [])
        except Exception as e:
            ai_summary = "AI investigation assistance is currently unavailable."
            ai_confidence = "N/A"
            ai_limitations = ["Failed to query local LLM service."]

        if ai_summary:
            # Simple sanitization of markup characters that reportlab might parse as HTML and crash
            clean_summary = ai_summary.replace("<", "&lt;").replace(">", "&gt;")
            paragraphs = clean_summary.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip().replace("\n", "<br/>"), styles["BodyTextDark"]))
                    story.append(Spacer(1, 8))
        
        story.append(Spacer(1, 10))
        limitations_str = ", ".join(ai_limitations) if ai_limitations else "None identified."
        story.append(Paragraph(f"<b>AI Interpretation Confidence:</b> {ai_confidence}", styles["BodyTextDark"]))
        story.append(Paragraph(f"<b>Evidence Gaps / Limitations Identified by AI:</b> {limitations_str}", styles["BodyTextDark"]))
        story.append(Spacer(1, 20))

        # --- PART III: INVESTIGATOR OBSERVATIONS ---
        story.append(Paragraph("PART III: INVESTIGATOR OBSERVATIONS (MANUAL REMARKS)", styles["SectionHeading"]))
        story.append(Paragraph(
            "This section records manual remarks, case hypothesis, and initial case notes entered by the assigned investigator.",
            styles["BodyTextDark"]
        ))
        
        # Display case description
        case_description_text = case.description or "No case description provided by the investigator."
        story.append(Paragraph(f"<b>Initial Case Notes / Objective:</b>", styles["BodyTextBold"]))
        story.append(Paragraph(case_description_text, styles["BodyTextDark"]))
        story.append(Spacer(1, 15))
        
        # Add blank lines/ruled notes area for investigator to write physical notes on printed/exported report
        story.append(Paragraph("<b>Examiner Observations & Log Notes:</b>", styles["BodyTextBold"]))
        story.append(Spacer(1, 10))
        
        note_lines = [
            [""],
            [""],
            [""],
            [""],
            [""]
        ]
        notes_table = Table(note_lines, colWidths=[500], rowHeights=[20]*5)
        notes_table.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(notes_table)
        story.append(Spacer(1, 20))

        # --- SECTION 5: AUDIT LOGS ---
        story.append(Paragraph("5. System Investigation Audit Trail", styles["SectionHeading"]))
        story.append(Paragraph(
            "Immutable audit log records detailing investigator queries, report configurations, and analyses run inside this case file:",
            styles["BodyTextDark"]
        ))
        
        audit_data = [[
            Paragraph("Timestamp", styles["TableCellHeader"]),
            Paragraph("Action", styles["TableCellHeader"]),
            Paragraph("Investigator details / Queries", styles["TableCellHeader"])
        ]]
        for log in audit_logs[:10]:
            audit_data.append([
                Paragraph(log.timestamp.strftime("%Y-%m-%d %H:%M:%S"), styles["TableCell"]),
                Paragraph(log.action, styles["TableCell"]),
                Paragraph(log.details or "N/A", styles["TableCell"])
            ])
            
        audit_table = Table(audit_data, colWidths=[110, 100, 290])
        audit_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4A5568")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(audit_table)

        # Build Document
        doc.build(story, canvasmaker=NumberedCanvas)

        # 2. Record report file in reports table
        report_record = Report(
            case_id=case_id,
            location=filepath
        )
        db.add(report_record)
        db.commit()

        return filepath
