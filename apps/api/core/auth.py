"""
PrepAI — JWT Auth middleware + rate limiting.
Validates Supabase JWTs and enforces plan-based rate limits via Redis.
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional

import jwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.config import get_settings
from apps.api.db.postgres import get_db
from apps.api.user.models import User

logger = logging.getLogger(__name__)
settings = get_settings()
security = HTTPBearer(auto_error=False)

# Redis client for rate limiting
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create the Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


@dataclass
class UserContext:
    """Authenticated user context passed to route handlers."""
    id: str
    supabase_id: str
    email: str
    full_name: str
    plan: str
    interviews_used_this_month: int


def decode_supabase_jwt(token: str) -> dict:
    """Decode and validate a Supabase JWT.

    Returns the decoded payload or raises HTTPException.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={
                "verify_aud": bool(settings.SUPABASE_JWT_SECRET),
                "verify_exp": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """FastAPI dependency: decode JWT, look up user, create if first login.

    Also enforces rate limiting per user.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    token = credentials.credentials
    payload = decode_supabase_jwt(token)

    supabase_id = payload.get("sub")
    email = payload.get("email", "")
    user_metadata = payload.get("user_metadata", {})
    full_name = user_metadata.get("full_name", user_metadata.get("name", ""))

    if not supabase_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # Look up user in Postgres
    result = await db.execute(
        select(User).where(User.supabase_id == supabase_id)
    )
    user = result.scalar_one_or_none()

    # Auto-create on first login
    if user is None:
        user = User(
            supabase_id=supabase_id,
            email=email,
            full_name=full_name,
            plan="free",
            interviews_used_this_month=0,
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created new user: {email} (supabase_id={supabase_id})")

    # Rate limiting via Redis
    await _check_rate_limit(str(user.id), user.plan)

    return UserContext(
        id=str(user.id),
        supabase_id=user.supabase_id,
        email=user.email,
        full_name=user.full_name,
        plan=user.plan,
        interviews_used_this_month=user.interviews_used_this_month,
    )


async def _check_rate_limit(user_id: str, plan: str) -> None:
    """Enforce per-user rate limits using Redis sliding window."""
    try:
        redis = await get_redis()
        limit = settings.RATE_LIMIT_PRO if plan == "pro" else settings.RATE_LIMIT_FREE
        key = f"rate_limit:{user_id}"
        now = time.time()
        window = 3600  # 1 hour

        pipe = redis.pipeline()
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, now - window)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in window
        pipe.zcard(key)
        # Set TTL on the key
        pipe.expire(key, window)
        results = await pipe.execute()

        request_count = results[2]

        if request_count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. {limit} requests per hour allowed for {plan} plan.",
                headers={"Retry-After": "60"},
            )
    except aioredis.ConnectionError:
        # If Redis is down, allow the request but log the error
        logger.warning("Redis unavailable for rate limiting — allowing request")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
