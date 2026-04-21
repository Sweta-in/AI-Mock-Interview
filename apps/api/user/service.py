"""
PrepAI — User service layer.
"""

import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.user.models import User

logger = logging.getLogger(__name__)


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Fetch a user by their UUID."""
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    return result.scalar_one_or_none()


async def get_user_by_supabase_id(db: AsyncSession, supabase_id: str) -> Optional[User]:
    """Fetch a user by their Supabase ID."""
    result = await db.execute(select(User).where(User.supabase_id == supabase_id))
    return result.scalar_one_or_none()


async def increment_interview_count(db: AsyncSession, user_id: str) -> None:
    """Increment the user's monthly interview usage counter."""
    await db.execute(
        update(User)
        .where(User.id == UUID(user_id))
        .values(interviews_used_this_month=User.interviews_used_this_month + 1)
    )
    await db.flush()


async def reset_monthly_counts(db: AsyncSession) -> int:
    """Reset all users' monthly interview counts. Returns count of users updated."""
    result = await db.execute(
        update(User)
        .where(User.interviews_used_this_month > 0)
        .values(interviews_used_this_month=0)
    )
    await db.flush()
    return result.rowcount  # type: ignore


async def update_user_plan(db: AsyncSession, user_id: str, plan: str) -> User:
    """Update a user's plan tier."""
    await db.execute(
        update(User)
        .where(User.id == UUID(user_id))
        .values(plan=plan)
    )
    await db.flush()
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found after update")
    return user
