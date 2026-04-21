"""
PrepAI — Feedback API router.
Endpoints for viewing feedback and skill snapshots.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.auth import get_current_user, UserContext
from apps.api.db.postgres import get_db
from apps.api.interview import service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/skills")
async def get_skill_snapshots(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the user's skill snapshots over time for the dashboard chart."""
    snapshots = await service.get_skill_snapshots(db, current_user.id, limit)
    return {
        "snapshots": [
            {
                "snapshot_date": s.snapshot_date.isoformat(),
                "skill_scores": s.skill_scores,
                "interviews_count": s.interviews_count,
                "role_id": str(s.role_id) if s.role_id else None,
            }
            for s in snapshots
        ],
    }


@router.get("/interview/{interview_id}")
async def get_interview_feedback(
    interview_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all feedback items for a specific interview."""
    interview = await service.get_interview(db, interview_id, current_user.id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    feedback_list = []
    for f in interview.feedback_items:
        feedback_list.append({
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
        "interview_id": interview_id,
        "status": interview.status,
        "overall_score": interview.overall_score,
        "feedback": feedback_list,
    }
