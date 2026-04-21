"""
PrepAI — User API router.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.auth import get_current_user, UserContext
from apps.api.db.postgres import get_db
from apps.api.user import service as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_current_user_profile(
    current_user: UserContext = Depends(get_current_user),
) -> dict:
    """Return the authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "plan": current_user.plan,
        "interviews_used_this_month": current_user.interviews_used_this_month,
    }


@router.patch("/me")
async def update_profile(
    updates: dict,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update the current user's profile fields."""
    allowed_fields = {"full_name"}
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}

    if not filtered:
        return {"message": "No valid fields to update"}

    from apps.api.user.models import User
    from sqlalchemy import update
    from uuid import UUID

    await db.execute(
        update(User)
        .where(User.id == UUID(current_user.id))
        .values(**filtered)
    )

    return {"message": "Profile updated", "updated_fields": list(filtered.keys())}
