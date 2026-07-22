from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Any, Dict, List, Optional

# --- Auth & User Schemas ---

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "user"

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# --- Document Schemas ---

class DocumentBase(BaseModel):
    filename: str
    doc_type: str
    status: str

class DocumentCreate(DocumentBase):
    user_id: int
    file_path: str
    file_hash: str

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    doc_type: str
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_score: float
    status: str
    file_hash: Optional[str] = None
    is_fake: bool
    blur_score: float
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Audit Log Schemas ---

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Analytics & Dashboard Schemas ---

class MonthlyVolume(BaseModel):
    label: str
    count: int

class StatsDashboardResponse(BaseModel):
    total_documents: int
    processed_documents: int
    failed_documents: int
    average_confidence: float
    fake_count: int
    blur_count: int
    doc_type_distribution: Dict[str, int]
    processing_history: List[MonthlyVolume]
