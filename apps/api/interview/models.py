"""
PrepAI — Interview, Question, Response, Feedback, and SkillSnapshot models.
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Text, Boolean,
    ForeignKey, Enum as SAEnum, UniqueConstraint, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from apps.api.db.postgres import Base


class InterviewRole(Base):
    __tablename__ = "interview_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    competencies = Column(ARRAY(String), nullable=False, default=list)
    system_prompt_template = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    interviews = relationship("Interview", back_populates="role", lazy="selectin")

    def __repr__(self) -> str:
        return f"<InterviewRole {self.slug}>"


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_user_id", "user_id"),
        Index("ix_interviews_status", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(
        SAEnum(
            "created", "active", "completed", "abandoned", "error",
            name="interview_status",
            create_type=True,
        ),
        nullable=False,
        default="created",
    )
    difficulty = Column(
        SAEnum("easy", "medium", "hard", name="interview_difficulty", create_type=True),
        nullable=False,
        default="medium",
    )
    interview_type = Column(
        SAEnum(
            "technical", "behavioral", "mixed",
            name="interview_type_enum",
            create_type=True,
        ),
        nullable=False,
        default="mixed",
    )
    config = Column(JSONB, nullable=True, default=dict)
    resume_text = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    overall_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    behavioral_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="interviews")
    role = relationship("InterviewRole", back_populates="interviews")
    questions = relationship(
        "InterviewQuestion",
        back_populates="interview",
        lazy="selectin",
        order_by="InterviewQuestion.sequence_num",
    )
    responses = relationship(
        "InterviewResponse",
        back_populates="interview",
        lazy="selectin",
    )
    feedback_items = relationship(
        "FeedbackItem",
        back_populates="interview",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Interview {self.id} status={self.status}>"


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        Index("ix_interview_questions_interview_seq", "interview_id", "sequence_num"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_num = Column(Integer, nullable=False)
    question_type = Column(
        SAEnum(
            "technical", "behavioral", "situational", "followup", "system_design",
            name="question_type_enum",
            create_type=True,
        ),
        nullable=False,
    )
    question_text = Column(Text, nullable=False)
    parent_question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    generation_context = Column(JSONB, nullable=True)
    asked_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    interview = relationship("Interview", back_populates="questions")
    parent_question = relationship("InterviewQuestion", remote_side=[id])
    response = relationship(
        "InterviewResponse",
        back_populates="question",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<InterviewQuestion seq={self.sequence_num} type={self.question_type}>"


class InterviewResponse(Base):
    __tablename__ = "interview_responses"
    __table_args__ = (
        Index("ix_interview_responses_interview_id", "interview_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_text = Column(Text, nullable=False)
    input_mode = Column(String(50), nullable=False, default="text")
    word_count = Column(Integer, nullable=True)
    response_time_seconds = Column(Float, nullable=True)
    score_relevance = Column(Float, nullable=True)
    score_depth = Column(Float, nullable=True)
    score_clarity = Column(Float, nullable=True)
    score_communication = Column(Float, nullable=True)
    score_technical_accuracy = Column(Float, nullable=True)

    # Relationships
    interview = relationship("Interview", back_populates="responses")
    question = relationship("InterviewQuestion", back_populates="response")
    feedback_item = relationship(
        "FeedbackItem",
        back_populates="response",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<InterviewResponse q={self.question_id}>"


class FeedbackItem(Base):
    __tablename__ = "feedback_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_responses.id", ondelete="SET NULL"),
        nullable=True,
    )
    feedback_level = Column(
        SAEnum("answer", "session", name="feedback_level_enum", create_type=True),
        nullable=False,
        default="answer",
    )
    strengths = Column(ARRAY(String), nullable=False, default=list)
    weaknesses = Column(ARRAY(String), nullable=False, default=list)
    improvements = Column(ARRAY(String), nullable=False, default=list)
    example_answer = Column(Text, nullable=True)
    keywords_used = Column(ARRAY(String), nullable=False, default=list)
    keywords_missed = Column(ARRAY(String), nullable=False, default=list)
    raw_llm_output = Column(JSONB, nullable=True)

    # Relationships
    interview = relationship("Interview", back_populates="feedback_items")
    response = relationship("InterviewResponse", back_populates="feedback_item")

    def __repr__(self) -> str:
        return f"<FeedbackItem level={self.feedback_level}>"


class UserSkillSnapshot(Base):
    __tablename__ = "user_skill_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "snapshot_date", name="uq_user_role_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_date = Column(Date, nullable=False, default=date.today)
    skill_scores = Column(JSONB, nullable=False, default=dict)
    interviews_count = Column(Integer, nullable=False, default=0)

    # Relationships
    user = relationship("User", back_populates="skill_snapshots")

    def __repr__(self) -> str:
        return f"<UserSkillSnapshot user={self.user_id} date={self.snapshot_date}>"
