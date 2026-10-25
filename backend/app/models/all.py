import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class PriorityEnum(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="Investigator")  # Investigator, Admin, Auditor
    
    cases = relationship("Case", back_populates="investigator")
    audit_logs = relationship("AuditLog", back_populates="user")

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    incident_type = Column(String, default="General")  # General, Phishing, Malware, DataBreach, etc.
    severity = Column(String, default="Medium")  # Low, Medium, High, Critical
    status = Column(String, default="Open")  # Open, Investigating, Resolved, Closed
    investigator_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    investigator = relationship("User")
    case = relationship("Case", back_populates="incidents")

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="Active")  # Active, Closed, Archived
    priority = Column(String, default="Medium")  # Low, Medium, High, Critical
    investigator_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    investigator = relationship("User", back_populates="cases")
    incidents = relationship("Incident", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    behavior_profiles = relationship("BehaviorProfile", back_populates="case", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="case", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="case", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False)  # SMS, Call, GPS, BrowserHistory, Contact, Application, File, Notification, WiFi, Bluetooth
    source = Column(String, nullable=False)          # e.g., "SMS_Backup.xml", "Chrome_History.db"
    hash = Column(String, nullable=False)            # SHA-256 integrity hash
    timestamp = Column(DateTime, nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)     # JSON-serialized metadata dictionary
    
    case = relationship("Case", back_populates="evidence")
    access_logs = relationship("EvidenceAccessLog", back_populates="evidence", cascade="all, delete-orphan")

class EvidenceAccessLog(Base):
    __tablename__ = "evidence_access_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # upload, view, download, analysis, report_generation
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    remarks = Column(String, nullable=True)
    
    evidence = relationship("Evidence", back_populates="access_logs")
    user = relationship("User")

class BehaviorProfile(Base):
    __tablename__ = "behavior_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    case = relationship("Case", back_populates="behavior_profiles")

class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String, nullable=False)      # Phishing, Anomaly, Call, Transaction, Application, File
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    evidence_references = Column(Text, nullable=True) # JSON-serialized list of evidence IDs
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    case = relationship("Case", back_populates="timeline_events")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    generated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    location = Column(String, nullable=False)        # Filepath to PDF
    
    case = relationship("Case", back_populates="reports")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)          # LOGIN, UPLOAD_EVIDENCE, RUN_ANALYSIS, EXPORT_REPORT
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    details = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="audit_logs")

class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    indicator_type = Column(String, nullable=False)  # hash, domain, package_name, url, phone_number
    value = Column(String, nullable=False, unique=True, index=True)
    threat_name = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # Low, Medium, High, Critical
    description = Column(String, nullable=True)
