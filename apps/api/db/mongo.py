"""
PrepAI — MongoDB async client setup using Motor.
Stores interview transcripts as rich documents.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import TypedDict, List, Optional, Any
from datetime import datetime
from apps.api.core.config import get_settings

settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


# ── Typed Document Schemas ───────────────────────────────────────────────────

class EvalScores(TypedDict, total=False):
    relevance: float
    depth: float
    clarity: float
    communication: float
    technical_accuracy: float


class TurnDict(TypedDict, total=False):
    turn_id: str
    role: str                        # "interviewer" or "candidate"
    content: str
    question_type: Optional[str]     # "technical", "behavioral", "followup"
    word_count: Optional[int]
    response_time_s: Optional[float]
    eval_scores: Optional[EvalScores]
    timestamp: str                   # ISO 8601


class TranscriptDocument(TypedDict, total=False):
    _id: str                         # == interview_id from Postgres
    interview_id: str
    user_id: str
    role: str                        # role slug
    turns: List[TurnDict]
    context_window_used: int
    total_tokens: int
    created_at: datetime


# ── Client Management ────────────────────────────────────────────────────────

async def connect_mongo() -> AsyncIOMotorDatabase:
    """Initialize the Motor client and return the database handle."""
    global _client, _db
    _client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=10,
        minPoolSize=2,
        serverSelectionTimeoutMS=5000,
    )
    _db = _client[settings.MONGODB_DB_NAME]

    # Ensure indexes
    transcripts = _db["transcripts"]
    await transcripts.create_index("interview_id", unique=True)
    await transcripts.create_index("user_id")
    await transcripts.create_index("created_at")

    return _db


async def close_mongo() -> None:
    """Close the Motor client."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the current database handle. Raises if not connected."""
    if _db is None:
        raise RuntimeError("MongoDB is not connected. Call connect_mongo() first.")
    return _db


# ── Transcript Operations ────────────────────────────────────────────────────

async def create_transcript(doc: TranscriptDocument) -> str:
    """Insert a new transcript document. Returns the document _id."""
    db = get_mongo_db()
    result = await db["transcripts"].insert_one(dict(doc))
    return str(result.inserted_id)


async def get_transcript(interview_id: str) -> Optional[TranscriptDocument]:
    """Retrieve a transcript by interview_id."""
    db = get_mongo_db()
    doc = await db["transcripts"].find_one({"interview_id": interview_id})
    return doc  # type: ignore


async def append_turn(interview_id: str, turn: TurnDict) -> None:
    """Append a turn to an existing transcript."""
    db = get_mongo_db()
    await db["transcripts"].update_one(
        {"interview_id": interview_id},
        {"$push": {"turns": dict(turn)}},
    )


async def update_turn_scores(
    interview_id: str,
    turn_id: str,
    eval_scores: EvalScores,
) -> None:
    """Update eval_scores on a specific turn."""
    db = get_mongo_db()
    await db["transcripts"].update_one(
        {"interview_id": interview_id, "turns.turn_id": turn_id},
        {"$set": {"turns.$.eval_scores": dict(eval_scores)}},
    )


async def update_transcript_tokens(
    interview_id: str,
    context_window_used: int,
    total_tokens: int,
) -> None:
    """Update token usage counters on the transcript."""
    db = get_mongo_db()
    await db["transcripts"].update_one(
        {"interview_id": interview_id},
        {
            "$set": {
                "context_window_used": context_window_used,
                "total_tokens": total_tokens,
            }
        },
    )
