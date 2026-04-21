"""
PrepAI — Socket.IO WebSocket server setup.
Handles real-time interview events: join, submit_answer, question delivery.
"""

import logging
from typing import Optional

import socketio

from apps.api.core.config import get_settings
from apps.api.interview.engine import InterviewEngine, ResponseData

logger = logging.getLogger(__name__)
settings = get_settings()

# Create Socket.IO server (async mode)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.allowed_origins_list,
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# Initialize the interview engine with the Socket.IO server
engine = InterviewEngine(sio=sio)


@sio.event
async def connect(sid: str, environ: dict) -> None:
    """Client connected to WebSocket."""
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    """Client disconnected from WebSocket."""
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def join_interview(sid: str, data: dict) -> None:
    """Client requests to join an interview room.

    Expected data: {interview_id: str, session_token: str}
    """
    interview_id = data.get("interview_id")
    session_token = data.get("session_token")

    if not interview_id or not session_token:
        await sio.emit("error", {
            "code": "INVALID_REQUEST",
            "message": "interview_id and session_token are required",
        }, to=sid)
        return

    # Validate session token
    from apps.api.db.postgres import async_session_factory
    from apps.api.interview.service import get_interview_by_session_token

    try:
        async with async_session_factory() as db:
            interview = await get_interview_by_session_token(db, session_token)

            if interview is None:
                await sio.emit("error", {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid session token",
                }, to=sid)
                return

            if str(interview.id) != interview_id:
                await sio.emit("error", {
                    "code": "TOKEN_MISMATCH",
                    "message": "Session token does not match interview ID",
                }, to=sid)
                return

            if interview.status not in ("created", "active"):
                await sio.emit("error", {
                    "code": "INTERVIEW_NOT_ACTIVE",
                    "message": f"Interview status is '{interview.status}', cannot join",
                }, to=sid)
                return

        # Join the interview room
        sio.enter_room(sid, interview_id)
        logger.info(f"Client {sid} joined interview room {interview_id}")

        # Start the interview engine
        await engine.start(interview_id)

    except Exception as e:
        logger.error(f"Error joining interview: {e}", exc_info=True)
        await sio.emit("error", {
            "code": "SERVER_ERROR",
            "message": "Failed to join interview session",
        }, to=sid)


@sio.event
async def submit_answer(sid: str, data: dict) -> None:
    """Client submits an answer to the current question.

    Expected data: {
        interview_id: str,
        question_id: str,
        response_text: str,
        response_time_seconds: float
    }
    """
    interview_id = data.get("interview_id")
    question_id = data.get("question_id")
    response_text = data.get("response_text", "").strip()
    response_time = data.get("response_time_seconds", 0)

    if not all([interview_id, question_id, response_text]):
        await sio.emit("error", {
            "code": "INVALID_REQUEST",
            "message": "interview_id, question_id, and response_text are required",
        }, to=sid)
        return

    if len(response_text) > 5000:
        await sio.emit("error", {
            "code": "RESPONSE_TOO_LONG",
            "message": "Response must be under 5000 characters",
        }, to=sid)
        return

    try:
        response = ResponseData(
            question_id=question_id,
            response_text=response_text,
            response_time_seconds=float(response_time),
        )

        await engine.advance(interview_id, response)

    except Exception as e:
        logger.error(f"Error processing answer: {e}", exc_info=True)
        await sio.emit("error", {
            "code": "PROCESSING_ERROR",
            "message": "Failed to process your answer. Please try again.",
        }, to=sid)


# Create the ASGI app for mounting
socket_app = socketio.ASGIApp(sio)
