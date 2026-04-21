"""
PrepAI — Celery task definitions for async evaluation.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from celery import Task
from apps.api.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in a synchronous Celery worker."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, soft_time_limit=30)
def evaluate_response_task(
    self: Task,
    question_id: str,
    response_id: str,
    interview_id: str,
    question_text: str,
    expected_components: List[str],
    response_text: str,
    recent_context: List[Dict[str, str]],
    role: str,
    difficulty: str,
) -> Dict[str, Any]:
    """Celery task for evaluating a candidate's response asynchronously.

    Steps:
    1. Call the AI evaluator
    2. Save scores to interview_responses in Postgres
    3. Save feedback_items to Postgres
    4. Emit 'evaluation_complete' via Socket.IO to the interview room
    5. Update MongoDB transcript turn with eval_scores
    """
    try:
        result = _run_async(
            _evaluate_async(
                question_id=question_id,
                response_id=response_id,
                interview_id=interview_id,
                question_text=question_text,
                expected_components=expected_components,
                response_text=response_text,
                recent_context=recent_context,
                role=role,
                difficulty=difficulty,
            )
        )
        return result
    except Exception as exc:
        logger.error(f"Evaluation task failed: {exc}", exc_info=True)
        self.retry(exc=exc, countdown=2 ** self.request.retries)
        return {"error": str(exc)}


async def _evaluate_async(
    question_id: str,
    response_id: str,
    interview_id: str,
    question_text: str,
    expected_components: List[str],
    response_text: str,
    recent_context: List[Dict[str, str]],
    role: str,
    difficulty: str,
) -> Dict[str, Any]:
    """Async implementation of the evaluation task."""
    from apps.api.ai.evaluator import Evaluator
    from apps.api.ai.llm import LLMClient
    from apps.api.db.postgres import async_session_factory
    from apps.api.interview import service as interview_service
    from apps.api.db.mongo import update_turn_scores, EvalScores

    llm = LLMClient()
    evaluator = Evaluator(llm)

    # 1. Call the evaluator
    eval_result = await evaluator.evaluate_answer(
        question_text=question_text,
        expected_components=expected_components,
        response_text=response_text,
        recent_context=recent_context,
        role=role,
        difficulty=difficulty,
        interview_id=interview_id,
    )

    scores = eval_result.get("scores", {})

    # 2. Save scores to interview_responses in Postgres
    async with async_session_factory() as db:
        await interview_service.update_response_scores(db, response_id, scores)

        # 3. Save feedback_items to Postgres
        await interview_service.save_feedback_item(
            db=db,
            interview_id=interview_id,
            response_id=response_id,
            feedback_level="answer",
            strengths=eval_result.get("specific_strengths", []),
            weaknesses=eval_result.get("specific_weaknesses", []),
            improvements=eval_result.get("components_missed", []),
            example_answer=None,
            keywords_used=eval_result.get("keywords_used", []),
            keywords_missed=eval_result.get("keywords_missed", []),
            raw_llm_output=eval_result,
        )
        await db.commit()

    # 4. Emit evaluation_complete via Socket.IO
    try:
        from apps.api.core.websocket import sio
        await sio.emit(
            "evaluation_complete",
            {
                "question_id": question_id,
                "scores": scores,
                "strengths": eval_result.get("specific_strengths", []),
                "weaknesses": eval_result.get("specific_weaknesses", []),
            },
            room=interview_id,
        )
    except Exception as e:
        logger.warning(f"Failed to emit Socket.IO event from Celery: {e}")

    # 5. Update MongoDB transcript turn with eval_scores
    try:
        eval_scores: EvalScores = {
            "relevance": scores.get("relevance", 0),
            "depth": scores.get("depth", 0),
            "clarity": scores.get("clarity", 0),
            "communication": scores.get("communication", 0),
            "technical_accuracy": scores.get("technical_accuracy", 0),
        }
        # Find the turn_id — use the response_id as a proxy
        await update_turn_scores(interview_id, response_id, eval_scores)
    except Exception as e:
        logger.warning(f"Failed to update MongoDB turn scores: {e}")

    return {
        "status": "completed",
        "scores": scores,
        "question_id": question_id,
        "response_id": response_id,
    }
