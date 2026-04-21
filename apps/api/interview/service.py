"""
PrepAI — Interview service layer.
Handles CRUD operations for interviews, questions, responses, and feedback.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.interview.models import (
    Interview, InterviewRole, InterviewQuestion,
    InterviewResponse as InterviewResponseModel,
    FeedbackItem, UserSkillSnapshot,
)
from apps.api.interview.schemas import (
    InterviewCreateRequest, InterviewStatus, Difficulty, InterviewType,
)
from apps.api.user.models import User
from apps.api.db.mongo import create_transcript, TranscriptDocument

logger = logging.getLogger(__name__)


async def get_role_by_slug(db: AsyncSession, slug: str) -> Optional[InterviewRole]:
    """Look up an interview role by slug."""
    result = await db.execute(
        select(InterviewRole).where(
            InterviewRole.slug == slug,
            InterviewRole.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_all_active_roles(db: AsyncSession) -> List[InterviewRole]:
    """Get all active interview roles."""
    result = await db.execute(
        select(InterviewRole).where(InterviewRole.is_active == True).order_by(InterviewRole.display_name)
    )
    return list(result.scalars().all())


async def create_interview(
    db: AsyncSession,
    user_id: str,
    request: InterviewCreateRequest,
) -> Interview:
    """Create a new interview session and initialize the MongoDB transcript."""
    # Resolve role
    role = await get_role_by_slug(db, request.role_slug)
    if role is None:
        raise ValueError(f"Role not found: {request.role_slug}")

    # Generate session token
    session_token = secrets.token_urlsafe(32)

    interview = Interview(
        user_id=UUID(user_id),
        role_id=role.id,
        session_token=session_token,
        status="created",
        difficulty=request.difficulty.value,
        interview_type=request.interview_type.value,
        resume_text=request.resume_text,
        config={
            "max_questions": 10,
            "max_followups_per_question": 2,
            "answer_timeout_seconds": 300,
        },
    )
    db.add(interview)
    await db.flush()

    # Create MongoDB transcript document
    transcript: TranscriptDocument = {
        "_id": str(interview.id),
        "interview_id": str(interview.id),
        "user_id": user_id,
        "role": request.role_slug,
        "turns": [],
        "context_window_used": 0,
        "total_tokens": 0,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await create_transcript(transcript)
    except Exception as e:
        logger.error(f"Failed to create MongoDB transcript: {e}")
        # Don't fail the whole request — MongoDB is supplementary

    return interview


async def get_interview(
    db: AsyncSession,
    interview_id: str,
    user_id: Optional[str] = None,
) -> Optional[Interview]:
    """Get an interview by ID, optionally filtered by user."""
    query = (
        select(Interview)
        .options(
            selectinload(Interview.role),
            selectinload(Interview.questions).selectinload(InterviewQuestion.response),
            selectinload(Interview.feedback_items),
        )
        .where(Interview.id == UUID(interview_id))
    )
    if user_id:
        query = query.where(Interview.user_id == UUID(user_id))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_interview_by_session_token(
    db: AsyncSession,
    session_token: str,
) -> Optional[Interview]:
    """Look up an interview by session token."""
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.role))
        .where(Interview.session_token == session_token)
    )
    return result.scalar_one_or_none()


async def list_interviews(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Interview], int]:
    """List interviews for a user with pagination."""
    offset = (page - 1) * page_size

    # Count total
    count_result = await db.execute(
        select(func.count(Interview.id)).where(Interview.user_id == UUID(user_id))
    )
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.role))
        .where(Interview.user_id == UUID(user_id))
        .order_by(Interview.started_at.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    interviews = list(result.scalars().all())

    return interviews, total


async def start_interview(db: AsyncSession, interview_id: str) -> Interview:
    """Mark an interview as active and set the start time."""
    await db.execute(
        update(Interview)
        .where(Interview.id == UUID(interview_id))
        .values(
            status="active",
            started_at=datetime.now(timezone.utc),
        )
    )
    await db.flush()
    interview = await get_interview(db, interview_id)
    if interview is None:
        raise ValueError(f"Interview {interview_id} not found after update")
    return interview


async def complete_interview(
    db: AsyncSession,
    interview_id: str,
    overall_score: float,
    technical_score: float,
    behavioral_score: float,
    communication_score: float,
) -> None:
    """Mark an interview as completed with final scores."""
    now = datetime.now(timezone.utc)
    interview = await get_interview(db, interview_id)
    if interview is None:
        raise ValueError(f"Interview {interview_id} not found")

    duration = None
    if interview.started_at:
        duration = int((now - interview.started_at).total_seconds())

    await db.execute(
        update(Interview)
        .where(Interview.id == UUID(interview_id))
        .values(
            status="completed",
            completed_at=now,
            duration_seconds=duration,
            overall_score=overall_score,
            technical_score=technical_score,
            behavioral_score=behavioral_score,
            communication_score=communication_score,
        )
    )
    await db.flush()


async def abandon_interview(db: AsyncSession, interview_id: str) -> None:
    """Mark an interview as abandoned."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Interview)
        .where(Interview.id == UUID(interview_id))
        .values(status="abandoned", completed_at=now)
    )
    await db.flush()


async def save_question(
    db: AsyncSession,
    interview_id: str,
    sequence_num: int,
    question_type: str,
    question_text: str,
    parent_question_id: Optional[str] = None,
    generation_context: Optional[dict] = None,
) -> InterviewQuestion:
    """Save a generated question to the database."""
    question = InterviewQuestion(
        interview_id=UUID(interview_id),
        sequence_num=sequence_num,
        question_type=question_type,
        question_text=question_text,
        parent_question_id=UUID(parent_question_id) if parent_question_id else None,
        generation_context=generation_context,
    )
    db.add(question)
    await db.flush()
    return question


async def save_response(
    db: AsyncSession,
    question_id: str,
    interview_id: str,
    response_text: str,
    response_time_seconds: float,
    input_mode: str = "text",
) -> InterviewResponseModel:
    """Save a candidate's response to the database."""
    word_count = len(response_text.split())
    response = InterviewResponseModel(
        question_id=UUID(question_id),
        interview_id=UUID(interview_id),
        response_text=response_text,
        input_mode=input_mode,
        word_count=word_count,
        response_time_seconds=response_time_seconds,
    )
    db.add(response)
    await db.flush()
    return response


async def update_response_scores(
    db: AsyncSession,
    response_id: str,
    scores: dict,
) -> None:
    """Update evaluation scores on a response."""
    await db.execute(
        update(InterviewResponseModel)
        .where(InterviewResponseModel.id == UUID(response_id))
        .values(
            score_relevance=scores.get("relevance"),
            score_depth=scores.get("depth"),
            score_clarity=scores.get("clarity"),
            score_communication=scores.get("communication"),
            score_technical_accuracy=scores.get("technical_accuracy"),
        )
    )
    await db.flush()


async def save_feedback_item(
    db: AsyncSession,
    interview_id: str,
    response_id: Optional[str],
    feedback_level: str,
    strengths: List[str],
    weaknesses: List[str],
    improvements: List[str],
    example_answer: Optional[str],
    keywords_used: List[str],
    keywords_missed: List[str],
    raw_llm_output: Optional[dict],
) -> FeedbackItem:
    """Save a feedback item."""
    item = FeedbackItem(
        interview_id=UUID(interview_id),
        response_id=UUID(response_id) if response_id else None,
        feedback_level=feedback_level,
        strengths=strengths,
        weaknesses=weaknesses,
        improvements=improvements,
        example_answer=example_answer,
        keywords_used=keywords_used,
        keywords_missed=keywords_missed,
        raw_llm_output=raw_llm_output,
    )
    db.add(item)
    await db.flush()
    return item


async def get_interview_questions(
    db: AsyncSession,
    interview_id: str,
) -> List[InterviewQuestion]:
    """Get all questions for an interview in order."""
    result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.interview_id == UUID(interview_id))
        .order_by(InterviewQuestion.sequence_num)
    )
    return list(result.scalars().all())


async def get_question_count(db: AsyncSession, interview_id: str) -> int:
    """Get count of primary (non-followup) questions asked."""
    result = await db.execute(
        select(func.count(InterviewQuestion.id))
        .where(
            InterviewQuestion.interview_id == UUID(interview_id),
            InterviewQuestion.parent_question_id == None,
        )
    )
    return result.scalar() or 0


async def save_skill_snapshot(
    db: AsyncSession,
    user_id: str,
    role_id: Optional[str],
    skill_scores: dict,
    interviews_count: int,
) -> UserSkillSnapshot:
    """Create or update a skill snapshot for today."""
    from datetime import date
    today = date.today()

    # Check for existing snapshot today
    query = select(UserSkillSnapshot).where(
        UserSkillSnapshot.user_id == UUID(user_id),
        UserSkillSnapshot.snapshot_date == today,
    )
    if role_id:
        query = query.where(UserSkillSnapshot.role_id == UUID(role_id))
    else:
        query = query.where(UserSkillSnapshot.role_id == None)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.skill_scores = skill_scores
        existing.interviews_count = interviews_count
        await db.flush()
        return existing
    else:
        snapshot = UserSkillSnapshot(
            user_id=UUID(user_id),
            role_id=UUID(role_id) if role_id else None,
            snapshot_date=today,
            skill_scores=skill_scores,
            interviews_count=interviews_count,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot


async def get_skill_snapshots(
    db: AsyncSession,
    user_id: str,
    limit: int = 30,
) -> List[UserSkillSnapshot]:
    """Get recent skill snapshots for a user."""
    result = await db.execute(
        select(UserSkillSnapshot)
        .where(UserSkillSnapshot.user_id == UUID(user_id))
        .order_by(UserSkillSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
