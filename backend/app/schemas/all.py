from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

# --- User Schemas ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Optional[str] = "Investigator"

class SecureAccessStart(BaseModel):
    email: EmailStr
    password: str

class SecureAccessVerify(BaseModel):
    challenge_id: str
    mfa_code: str = Field(min_length=6, max_length=6)
    biometric_assertion: str = Field(min_length=1)
    dsc_assertion: str = Field(min_length=1)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    reset_token: str
    password: str = Field(min_length=8)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str

# --- Incident Schemas ---
class IncidentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    incident_type: Optional[str] = "General"
    severity: Optional[str] = "Medium"
    case_id: Optional[str] = None

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    incident_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    case_id: Optional[str] = None

class IncidentResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    incident_type: str
    severity: str
    status: str
    investigator_id: str
    case_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Case Schemas ---
class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "Medium"  # Low, Medium, High, Critical

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # Active, Closed, Archived
    priority: Optional[str] = None  # Low, Medium, High, Critical

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    investigator_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Evidence Schemas ---
class EvidenceCreate(BaseModel):
    artifact_type: str
    source: str
    hash: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    artifact_type: str
    source: str
    hash: str
    timestamp: datetime
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

# --- Evidence Access Log Schemas ---
class EvidenceAccessLogCreate(BaseModel):
    evidence_id: str
    user_id: str
    action: str
    remarks: Optional[str] = None

class EvidenceAccessLogResponse(BaseModel):
    id: str
    evidence_id: str
    user_id: str
    action: str
    timestamp: datetime
    remarks: Optional[str]

    class Config:
        from_attributes = True

# --- Analysis & Anomaly Schemas ---
class AnomalyResponse(BaseModel):
    evidence_id: str
    timestamp: datetime
    artifact_type: str
    score: float
    explanation: str
    confidence: float
    details: Dict[str, Any]

class BehaviorProfileResponse(BaseModel):
    anomaly_score: float
    explanation: str
    anomalies: List[AnomalyResponse]

# --- Timeline Schemas ---
class TimelineEventResponse(BaseModel):
    id: str
    case_id: str
    timestamp: datetime
    event_type: str
    description: str
    confidence: float
    evidence_references: List[str]
    
    class Config:
        from_attributes = True

# --- Crime Reconstruction Schemas ---
class IncidentSequenceStep(BaseModel):
    step_number: int
    event_type: str
    description: str
    timestamp: datetime
    evidence_references: List[str]

class CrimeReconstructionResponse(BaseModel):
    incident_type: str  # Phishing, Malware, Fraud, etc.
    explanation: str
    confidence: float
    steps: List[IncidentSequenceStep]

# --- Graph Schemas ---
class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # Contact, Application, Location, Case
    priority_score: float = 0.0
    degree_centrality: float = 0.0
    betweenness_centrality: float = 0.0

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    weight: float = 1.0

class CommunicationGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

# --- AI Copilot Schemas ---
class CopilotQuery(BaseModel):
    case_id: str
    question: str

class CopilotResponse(BaseModel):
    answer: str
    retrieved_evidence: List[EvidenceResponse]

class AIQueryRequest(BaseModel):
    question: str

class AIQueryResponse(BaseModel):
    answer: str
    evidence_references: List[str]
    timeline_references: List[str]
    confidence: str
    limitations: List[str]
    retrieved_evidence: Optional[List[EvidenceResponse]] = None

# --- Audit Schemas ---
class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    user_name: Optional[str]
    action: str
    timestamp: datetime
    details: Optional[str]
    
    class Config:
        from_attributes = True

class AuditLogPaginatedResponse(BaseModel):
    items: List[AuditLogResponse]
    total_count: int
