from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Analysis ─────────────────────────────────────────────────────────────────

class ConditionScore(BaseModel):
    name: str
    confidence: float   # 0.0 – 1.0


class AnalyzeResponse(BaseModel):
    predicted_condition: str
    confidence: float
    all_scores: List[ConditionScore]
    analysis_time_seconds: float
    disclaimer: str = (
        "This is an AI-generated preliminary analysis and does NOT replace "
        "professional medical diagnosis. Always consult a qualified "
        "dermatologist for accurate assessment and treatment."
    )


# ── History ──────────────────────────────────────────────────────────────────

class HistoryRecord(BaseModel):
    id: int
    predicted_condition: str
    confidence: float
    all_scores: List[ConditionScore]
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    records: List[HistoryRecord]
    total: int
