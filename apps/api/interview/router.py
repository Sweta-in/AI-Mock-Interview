"""
PrepAI — Interview API router.
Endpoints for creating, listing, starting, and managing interviews.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.auth import get_current_user, UserContext
from apps.api.core.config import get_settings
from apps.api.db.postgres import get_db
from apps.api.interview import service
from apps.api.interview.schemas import (
    InterviewCreateRequest,
    InterviewResponse,
    InterviewDetailResponse,
    InterviewListResponse,
    InterviewStartResponse,
    PlanLimitError,
    RoleResponse,
)
from apps.api.user.service import increment_interview_count

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> list[dict]:
    """List all available interview roles."""
    roles = await service.get_all_active_roles(db)
    return [
        {
            "id": str(r.id),
            "slug": r.slug,
            "display_name": r.display_name,
            "category": r.category,
            "competencies": r.competencies,
            "is_active": r.is_active,
        }
        for r in roles
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_interview(
    request: InterviewCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new interview session.

    Validates plan limits and initializes MongoDB transcript.
    Returns HTTP 402 if the user has exceeded their plan's interview limit.
    """
    # Plan limit check
    if current_user.plan == "free":
        if current_user.interviews_used_this_month >= settings.FREE_PLAN_INTERVIEW_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "plan_limit_reached",
                    "limit": settings.FREE_PLAN_INTERVIEW_LIMIT,
                    "plan": "free",
                },
            )

    try:
        interview = await service.create_interview(db, current_user.id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Increment usage counter
    await increment_interview_count(db, current_user.id)

    return {
        "id": str(interview.id),
        "session_token": interview.session_token,
        "status": interview.status,
        "role_slug": request.role_slug,
        "difficulty": request.difficulty.value,
        "interview_type": request.interview_type.value,
    }


@router.get("", response_model=InterviewListResponse)
async def list_interviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List the current user's interviews with pagination."""
    interviews, total = await service.list_interviews(
        db, current_user.id, page, page_size
    )

    return {
        "interviews": [
            {
                "id": str(i.id),
                "role_slug": i.role.slug if i.role else "unknown",
                "role_name": i.role.display_name if i.role else "Unknown",
                "status": i.status,
                "difficulty": i.difficulty,
                "interview_type": i.interview_type,
                "started_at": i.started_at,
                "completed_at": i.completed_at,
                "duration_seconds": i.duration_seconds,
                "overall_score": i.overall_score,
                "technical_score": i.technical_score,
                "behavioral_score": i.behavioral_score,
                "communication_score": i.communication_score,
                "question_count": len(i.questions) if hasattr(i, "questions") else 0,
            }
            for i in interviews
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{interview_id}")
async def get_interview(
    interview_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single interview with all questions and responses."""
    interview = await service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    questions = []
    responses = []
    feedback = []

    for q in interview.questions:
        questions.append({
            "id": str(q.id),
            "sequence_num": q.sequence_num,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "parent_question_id": str(q.parent_question_id) if q.parent_question_id else None,
            "asked_at": q.asked_at.isoformat() if q.asked_at else None,
        })
        if q.response:
            r = q.response
            responses.append({
                "id": str(r.id),
                "question_id": str(r.question_id),
                "response_text": r.response_text,
                "word_count": r.word_count,
                "response_time_seconds": r.response_time_seconds,
                "scores": {
                    "relevance": r.score_relevance,
                    "depth": r.score_depth,
                    "clarity": r.score_clarity,
                    "communication": r.score_communication,
                    "technical_accuracy": r.score_technical_accuracy,
                },
            })

    for f in interview.feedback_items:
        feedback.append({
            "id": str(f.id),
            "response_id": str(f.response_id) if f.response_id else None,
            "feedback_level": f.feedback_level,
            "strengths": f.strengths,
            "weaknesses": f.weaknesses,
            "improvements": f.improvements,
            "example_answer": f.example_answer,
            "keywords_used": f.keywords_used,
            "keywords_missed": f.keywords_missed,
        })

    return {
        "id": str(interview.id),
        "role_slug": interview.role.slug if interview.role else "unknown",
        "role_name": interview.role.display_name if interview.role else "Unknown",
        "status": interview.status,
        "difficulty": interview.difficulty,
        "interview_type": interview.interview_type,
        "started_at": interview.started_at,
        "completed_at": interview.completed_at,
        "duration_seconds": interview.duration_seconds,
        "overall_score": interview.overall_score,
        "technical_score": interview.technical_score,
        "behavioral_score": interview.behavioral_score,
        "communication_score": interview.communication_score,
        "question_count": len(questions),
        "questions": questions,
        "responses": responses,
        "feedback": feedback,
    }


@router.post("/{interview_id}/start")
async def start_interview(
    interview_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark an interview as active and return a WebSocket connection token."""
    interview = await service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if interview.status not in ("created", "active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start interview with status: {interview.status}",
        )

    if interview.status == "created":
        interview = await service.start_interview(db, interview_id)

    return {
        "interview_id": str(interview.id),
        "session_token": interview.session_token,
        "websocket_url": "/ws",
    }


@router.post("/{interview_id}/abandon")
async def abandon_interview(
    interview_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark an interview as abandoned."""
    interview = await service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if interview.status not in ("created", "active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot abandon interview with status: {interview.status}",
        )

    await service.abandon_interview(db, interview_id)
    return {"message": "Interview abandoned", "interview_id": interview_id}


@router.get("/{interview_id}/report")
async def get_interview_report(
    interview_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the final interview report. Returns partial report if still generating."""
    interview = await service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if interview.status == "active":
        return {"status": "in_progress", "message": "Interview is still in progress"}

    if interview.status in ("created",):
        return {"status": "not_started", "message": "Interview has not started yet"}

    # Find session-level feedback
    session_feedback = None
    for f in interview.feedback_items:
        if f.feedback_level == "session":
            session_feedback = f
            break

    if session_feedback is None and interview.status == "completed":
        return {"status": "generating", "message": "Report is being generated"}

    if session_feedback is None:
        return {
            "status": interview.status,
            "interview_id": interview_id,
            "overall_score": interview.overall_score,
            "message": "No detailed report available",
        }

    raw = session_feedback.raw_llm_output or {}
    return {
        "status": "ready",
        "interview_id": interview_id,
        "executive_summary": raw.get("executive_summary", ""),
        "overall_score": interview.overall_score,
        "dimension_scores": raw.get("dimension_scores", {}),
        "top_strengths": raw.get("top_strengths", session_feedback.strengths[:3]),
        "top_improvements": raw.get("top_improvements", session_feedback.improvements[:3]),
        "skill_breakdown": raw.get("skill_breakdown", {}),
        "recommended_next_steps": raw.get("recommended_next_steps", []),
        "comparison_benchmark": raw.get("comparison_benchmark", "mid"),
    }
