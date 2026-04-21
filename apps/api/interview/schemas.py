"""
PrepAI — Pydantic v2 schemas for interview API request/response models.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class InterviewStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ERROR = "error"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    MIXED = "mixed"


class QuestionType(str, Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SITUATIONAL = "situational"
    FOLLOWUP = "followup"
    SYSTEM_DESIGN = "system_design"


class FeedbackLevel(str, Enum):
    ANSWER = "answer"
    SESSION = "session"


# ── Request Schemas ──────────────────────────────────────────────────────────

class InterviewCreateRequest(BaseModel):
    role_slug: str = Field(..., min_length=1, max_length=100)
    difficulty: Difficulty = Field(default=Difficulty.MEDIUM)
    interview_type: InterviewType = Field(default=InterviewType.MIXED)
    resume_text: Optional[str] = Field(default=None, max_length=10000)

    @field_validator("role_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("role_slug must be alphanumeric with hyphens/underscores")
        return v.lower()


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    response_text: str = Field(..., min_length=1, max_length=5000)
    response_time_seconds: float = Field(..., ge=0, le=600)


# ── Response Schemas ─────────────────────────────────────────────────────────

class RoleResponse(BaseModel):
    id: str
    slug: str
    display_name: str
    category: str
    competencies: List[str]
    is_active: bool

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    question_id: str
    question_text: str
    question_num: int
    total_questions: int
    question_type: str

    model_config = {"from_attributes": True}


class ScoreMap(BaseModel):
    relevance: float = Field(ge=0, le=100)
    depth: float = Field(ge=0, le=100)
    clarity: float = Field(ge=0, le=100)
    communication: float = Field(ge=0, le=100)
    technical_accuracy: float = Field(ge=0, le=100)


class EvaluationResponse(BaseModel):
    question_id: str
    scores: ScoreMap
    strengths: List[str]
    weaknesses: List[str]
    improvements: List[str]
    keywords_used: List[str]
    keywords_missed: List[str]


class InterviewResponse(BaseModel):
    id: str
    role_slug: str
    role_name: str
    status: str
    difficulty: str
    interview_type: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    overall_score: Optional[float]
    technical_score: Optional[float]
    behavioral_score: Optional[float]
    communication_score: Optional[float]
    question_count: int = 0
    session_token: Optional[str] = None

    model_config = {"from_attributes": True}


class InterviewDetailResponse(InterviewResponse):
    questions: List[Dict[str, Any]] = []
    responses: List[Dict[str, Any]] = []
    feedback: List[Dict[str, Any]] = []


class InterviewListResponse(BaseModel):
    interviews: List[InterviewResponse]
    total: int
    page: int
    page_size: int


class InterviewStartResponse(BaseModel):
    interview_id: str
    session_token: str
    websocket_url: str


class ReportResponse(BaseModel):
    interview_id: str
    executive_summary: str
    overall_score: float
    dimension_scores: Dict[str, float]
    top_strengths: List[str]
    top_improvements: List[str]
    skill_breakdown: Dict[str, Any]
    recommended_next_steps: List[str]
    comparison_benchmark: str
    status: str = "ready"


class PlanLimitError(BaseModel):
    error: str = "plan_limit_reached"
    limit: int
    plan: str


# ── Skill Snapshot ───────────────────────────────────────────────────────────

class SkillSnapshotResponse(BaseModel):
    snapshot_date: str
    skill_scores: Dict[str, float]
    interviews_count: int
    role_slug: Optional[str] = None

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    user_name: str
    plan: str
    interviews_used: int
    interview_limit: int
    recent_interviews: List[InterviewResponse]
    skill_snapshots: List[SkillSnapshotResponse]
