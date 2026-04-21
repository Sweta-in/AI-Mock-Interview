"""
PrepAI — Feedback service layer.
"""

import logging
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.interview import service as interview_service

logger = logging.getLogger(__name__)


async def get_dashboard_data(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Aggregate dashboard data for the user."""
    interviews, total = await interview_service.list_interviews(db, user_id, page=1, page_size=5)
    snapshots = await interview_service.get_skill_snapshots(db, user_id, limit=30)

    # Compute running averages per skill dimension
    skill_trends: Dict[str, List[float]] = {}
    for snapshot in reversed(snapshots):
        for skill, score in snapshot.skill_scores.items():
            if skill not in skill_trends:
                skill_trends[skill] = []
            skill_trends[skill].append(score)

    return {
        "recent_interviews": interviews,
        "total_interviews": total,
        "skill_snapshots": snapshots,
        "skill_trends": skill_trends,
    }
