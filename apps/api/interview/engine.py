"""
PrepAI — InterviewEngine: core orchestration for multi-turn AI interviews.
Manages question flow, follow-up logic, speculative pre-fetching, and session state.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from apps.api.ai.llm import LLMClient
from apps.api.ai.prompts import (
    build_question_generation_prompt,
    build_followup_prompt,
)
from apps.api.ai.evaluator import Evaluator
from apps.api.db.postgres import async_session_factory
from apps.api.db.mongo import append_turn, get_transcript, update_transcript_tokens, TurnDict
from apps.api.interview import service as interview_service

logger = logging.getLogger(__name__)


@dataclass
class Question:
    """A generated interview question."""
    id: str
    text: str
    question_type: str
    topic_area: str
    expected_components: List[str]
    difficulty: str
    followup_triggers: Dict[str, str]
    sequence_num: int
    parent_question_id: Optional[str] = None


@dataclass
class ResponseData:
    """Incoming candidate response data."""
    question_id: str
    response_text: str
    response_time_seconds: float


@dataclass
class EvalResult:
    """Result of evaluating a candidate response."""
    scores: Dict[str, float]
    should_followup: bool
    followup_reason: str
    specific_strengths: List[str]
    specific_weaknesses: List[str]
    components_missed: List[str]
    raw: Dict[str, Any]


@dataclass
class InterviewSession:
    """In-memory state for an active interview session."""
    interview_id: str
    user_id: str
    role_slug: str
    role_display_name: str
    system_prompt: str
    difficulty: str
    interview_type: str
    competencies: List[str]
    turns: List[Dict[str, str]] = field(default_factory=list)
    topics_covered: List[str] = field(default_factory=list)
    primary_questions_asked: int = 0
    followups_for_current: int = 0
    current_question: Optional[Question] = None
    all_scores: List[Dict[str, float]] = field(default_factory=list)
    prefetched_question: Optional[Question] = None
    total_tokens: int = 0


class InterviewEngine:
    """Orchestrates multi-turn AI interviews with adaptive questioning."""

    MAX_QUESTIONS = 10
    MAX_FOLLOWUPS_PER_QUESTION = 2
    ANSWER_TIMEOUT_SECONDS = 300

    def __init__(
        self,
        sio: Any = None,
        llm: Optional[LLMClient] = None,
        evaluator: Optional[Evaluator] = None,
    ) -> None:
        self.sio = sio
        self.llm = llm or LLMClient()
        self.evaluator = evaluator or Evaluator(self.llm)
        self._sessions: Dict[str, InterviewSession] = {}

    async def start(self, interview_id: str) -> None:
        """Initialize and start an interview session.

        Loads interview data from DB, builds the session state,
        generates and delivers the first question.
        """
        session = await self._load_or_create_session(interview_id)
        self._sessions[interview_id] = session

        # Generate and deliver the first question
        question = await self._generate_and_deliver_question(session)
        session.current_question = question

        # Speculatively pre-fetch the next question in the background
        asyncio.create_task(self._prefetch_next_question(session))

    async def advance(self, interview_id: str, response: ResponseData) -> None:
        """Process a candidate response and advance the interview.

        1. Save the response
        2. Evaluate it (async — Celery if available, inline if not)
        3. Decide: follow-up or next primary question
        4. Generate and deliver the next question, or end the interview
        """
        session = self._sessions.get(interview_id)
        if session is None:
            # Attempt to reconstruct from DB
            session = await self._load_or_create_session(interview_id)
            self._sessions[interview_id] = session

        # Record the candidate's response as a turn
        turn: TurnDict = {
            "turn_id": str(uuid.uuid4()),
            "role": "candidate",
            "content": response.response_text,
            "word_count": len(response.response_text.split()),
            "response_time_s": response.response_time_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        session.turns.append({"role": "candidate", "content": response.response_text})

        # Save to MongoDB
        try:
            await append_turn(interview_id, turn)
        except Exception as e:
            logger.error(f"Failed to append turn to MongoDB: {e}")

        # Save response to Postgres
        async with async_session_factory() as db:
            db_response = await interview_service.save_response(
                db=db,
                question_id=response.question_id,
                interview_id=interview_id,
                response_text=response.response_text,
                response_time_seconds=response.response_time_seconds,
            )
            await db.commit()
            response_id = str(db_response.id)

        # Evaluate the response
        eval_result = await self._evaluate_response(session, response)

        # Save evaluation results
        async with async_session_factory() as db:
            await interview_service.update_response_scores(db, response_id, eval_result.scores)
            await interview_service.save_feedback_item(
                db=db,
                interview_id=interview_id,
                response_id=response_id,
                feedback_level="answer",
                strengths=eval_result.specific_strengths,
                weaknesses=eval_result.specific_weaknesses,
                improvements=eval_result.raw.get("components_missed", []),
                example_answer=None,
                keywords_used=eval_result.raw.get("keywords_used", []),
                keywords_missed=eval_result.raw.get("keywords_missed", []),
                raw_llm_output=eval_result.raw,
            )
            await db.commit()

        session.all_scores.append(eval_result.scores)

        # Emit evaluation results to the client
        if self.sio:
            await self.sio.emit(
                "evaluation_complete",
                {
                    "question_id": response.question_id,
                    "scores": eval_result.scores,
                    "strengths": eval_result.specific_strengths,
                    "weaknesses": eval_result.specific_weaknesses,
                },
                room=interview_id,
            )

        # Determine next action: follow-up, next question, or end
        if session.primary_questions_asked >= self.MAX_QUESTIONS:
            await self._end_interview(session)
            return

        should_followup = await self._determine_followup(eval_result, session)

        if should_followup:
            question = await self._generate_followup(session, eval_result)
        else:
            session.followups_for_current = 0
            session.primary_questions_asked += 1

            # Use pre-fetched question if available
            if session.prefetched_question:
                question = session.prefetched_question
                session.prefetched_question = None
                # Save to DB
                async with async_session_factory() as db:
                    await interview_service.save_question(
                        db=db,
                        interview_id=interview_id,
                        sequence_num=question.sequence_num,
                        question_type=question.question_type,
                        question_text=question.text,
                        generation_context={
                            "topic_area": question.topic_area,
                            "expected_components": question.expected_components,
                            "followup_triggers": question.followup_triggers,
                        },
                    )
                    await db.commit()
            else:
                question = await self._generate_and_deliver_question(session)

        session.current_question = question

        # Deliver the question
        if self.sio:
            await self.sio.emit(
                "question",
                {
                    "question_id": question.id,
                    "question_text": question.text,
                    "question_num": session.primary_questions_asked,
                    "total_questions": self.MAX_QUESTIONS,
                    "question_type": question.question_type,
                },
                room=interview_id,
            )

        # Record interviewer turn
        interviewer_turn: TurnDict = {
            "turn_id": str(uuid.uuid4()),
            "role": "interviewer",
            "content": question.text,
            "question_type": question.question_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        session.turns.append({"role": "interviewer", "content": question.text})
        try:
            await append_turn(interview_id, interviewer_turn)
        except Exception as e:
            logger.error(f"Failed to append interviewer turn to MongoDB: {e}")

        # Pre-fetch next question
        if session.primary_questions_asked < self.MAX_QUESTIONS:
            asyncio.create_task(self._prefetch_next_question(session))

    async def _generate_and_deliver_question(self, session: InterviewSession) -> Question:
        """Generate a new question using the LLM and save it to the database."""
        messages = build_question_generation_prompt(
            role_slug=session.role_slug,
            interview_type=session.interview_type,
            difficulty=session.difficulty,
            topics_covered=session.topics_covered,
            questions_asked=session.primary_questions_asked,
            remaining_turns=self.MAX_QUESTIONS - session.primary_questions_asked,
            performance_summary=self._get_performance_signal(session),
            recent_context=session.turns[-6:],
            competencies=session.competencies,
            system_prompt=session.system_prompt,
        )

        result = await self.llm.complete_json(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            interview_id=session.interview_id,
        )
        session.total_tokens += result.get("prompt_tokens", 0) + result.get("completion_tokens", 0)

        parsed = result["parsed"]
        sequence_num = session.primary_questions_asked + 1

        question = Question(
            id=str(uuid.uuid4()),
            text=parsed.get("question_text", "Could you tell me about your experience?"),
            question_type=parsed.get("question_type", "technical"),
            topic_area=parsed.get("topic_area", "general"),
            expected_components=parsed.get("expected_components", []),
            difficulty=parsed.get("difficulty", session.difficulty),
            followup_triggers=parsed.get("followup_triggers", {}),
            sequence_num=sequence_num,
        )

        # Track topic coverage
        if question.topic_area not in session.topics_covered:
            session.topics_covered.append(question.topic_area)

        # Save to Postgres
        async with async_session_factory() as db:
            db_question = await interview_service.save_question(
                db=db,
                interview_id=session.interview_id,
                sequence_num=question.sequence_num,
                question_type=question.question_type,
                question_text=question.text,
                generation_context={
                    "topic_area": question.topic_area,
                    "expected_components": question.expected_components,
                    "followup_triggers": question.followup_triggers,
                },
            )
            question.id = str(db_question.id)
            await db.commit()

        return question

    async def _determine_followup(
        self, eval_result: EvalResult, session: InterviewSession
    ) -> bool:
        """Decide whether to ask a follow-up question."""
        if session.followups_for_current >= self.MAX_FOLLOWUPS_PER_QUESTION:
            return False

        if not eval_result.should_followup:
            return False

        if eval_result.followup_reason == "none":
            return False

        # Don't follow up if we're running low on questions
        remaining = self.MAX_QUESTIONS - session.primary_questions_asked
        if remaining <= 2 and eval_result.followup_reason != "vague":
            return False

        return True

    async def _generate_followup(
        self, session: InterviewSession, eval_result: EvalResult
    ) -> Question:
        """Generate a follow-up question based on the evaluation result."""
        current = session.current_question
        if current is None:
            raise ValueError("Cannot generate follow-up without a current question")

        messages = build_followup_prompt(
            original_question=current.text,
            candidate_answer=session.turns[-1]["content"] if session.turns else "",
            followup_reason=eval_result.followup_reason,
            expected_components_missed=eval_result.components_missed,
            system_prompt=session.system_prompt,
        )

        result = await self.llm.complete(
            messages=messages,
            temperature=0.5,
            max_tokens=300,
            interview_id=session.interview_id,
        )
        session.total_tokens += result.get("prompt_tokens", 0) + result.get("completion_tokens", 0)

        followup_text = result["content"].strip()
        session.followups_for_current += 1

        question = Question(
            id=str(uuid.uuid4()),
            text=followup_text,
            question_type="followup",
            topic_area=current.topic_area,
            expected_components=eval_result.components_missed,
            difficulty=current.difficulty,
            followup_triggers={},
            sequence_num=current.sequence_num,
            parent_question_id=current.id,
        )

        # Save to Postgres
        async with async_session_factory() as db:
            db_question = await interview_service.save_question(
                db=db,
                interview_id=session.interview_id,
                sequence_num=question.sequence_num,
                question_type="followup",
                question_text=followup_text,
                parent_question_id=current.id,
                generation_context={
                    "followup_reason": eval_result.followup_reason,
                    "components_missed": eval_result.components_missed,
                },
            )
            question.id = str(db_question.id)
            await db.commit()

        return question

    async def _evaluate_response(
        self, session: InterviewSession, response: ResponseData
    ) -> EvalResult:
        """Evaluate the candidate's response using the AI evaluator."""
        current = session.current_question
        if current is None:
            # Fallback: return neutral scores
            return EvalResult(
                scores={"relevance": 50, "depth": 50, "clarity": 50, "communication": 50, "technical_accuracy": 50},
                should_followup=False,
                followup_reason="none",
                specific_strengths=["Response received"],
                specific_weaknesses=["Could not evaluate without question context"],
                components_missed=[],
                raw={},
            )

        raw = await self.evaluator.evaluate_answer(
            question_text=current.text,
            expected_components=current.expected_components,
            response_text=response.response_text,
            recent_context=session.turns[-3:],
            role=session.role_slug,
            difficulty=session.difficulty,
            interview_id=session.interview_id,
        )

        return EvalResult(
            scores=raw.get("scores", {}),
            should_followup=raw.get("should_followup", False),
            followup_reason=raw.get("followup_reason", "none"),
            specific_strengths=raw.get("specific_strengths", []),
            specific_weaknesses=raw.get("specific_weaknesses", []),
            components_missed=raw.get("components_missed", []),
            raw=raw,
        )

    async def _generate_final_report(
        self, interview_id: str, session: InterviewSession
    ) -> None:
        """Generate and save the final interview report."""
        report = await self.evaluator.generate_final_report(
            transcript=session.turns,
            all_scores=session.all_scores,
            role=session.role_slug,
            interview_type=session.interview_type,
            interview_id=interview_id,
        )

        # Save to Postgres
        async with async_session_factory() as db:
            # Update interview scores
            overall = report.get("overall_score", 50.0)
            dim_scores = report.get("dimension_scores", {})

            await interview_service.complete_interview(
                db=db,
                interview_id=interview_id,
                overall_score=overall,
                technical_score=dim_scores.get("technical_knowledge", overall),
                behavioral_score=dim_scores.get("problem_solving", overall),
                communication_score=dim_scores.get("communication", overall),
            )

            # Save session-level feedback
            await interview_service.save_feedback_item(
                db=db,
                interview_id=interview_id,
                response_id=None,
                feedback_level="session",
                strengths=report.get("top_strengths", []),
                weaknesses=[],
                improvements=report.get("top_improvements", []),
                example_answer=None,
                keywords_used=[],
                keywords_missed=[],
                raw_llm_output=report,
            )

            # Save skill snapshot
            skill_breakdown = report.get("skill_breakdown", {})
            skill_scores = {
                topic: data.get("score", 50) if isinstance(data, dict) else 50
                for topic, data in skill_breakdown.items()
            }
            await interview_service.save_skill_snapshot(
                db=db,
                user_id=session.user_id,
                role_id=None,  # Could look up role_id if needed
                skill_scores=skill_scores,
                interviews_count=1,
            )

            await db.commit()

        # Update MongoDB token usage
        try:
            await update_transcript_tokens(
                interview_id=interview_id,
                context_window_used=len(session.turns) * 200,  # Rough estimate
                total_tokens=session.total_tokens,
            )
        except Exception as e:
            logger.error(f"Failed to update MongoDB token counts: {e}")

    async def _end_interview(self, session: InterviewSession) -> None:
        """End the interview and generate the final report."""
        interview_id = session.interview_id
        logger.info(f"Ending interview {interview_id}")

        # Generate final report
        await self._generate_final_report(interview_id, session)

        # Emit completion event
        if self.sio:
            await self.sio.emit(
                "interview_complete",
                {"report_id": interview_id},
                room=interview_id,
            )

        # Clean up session
        self._sessions.pop(interview_id, None)

    def _get_performance_signal(self, session: InterviewSession) -> str:
        """Summarize the candidate's performance so far for question calibration."""
        if not session.all_scores:
            return "No responses yet — this is the beginning of the interview."

        all_avgs = []
        for score_set in session.all_scores:
            if score_set:
                avg = sum(score_set.values()) / len(score_set)
                all_avgs.append(avg)

        if not all_avgs:
            return "Scores pending evaluation."

        overall_avg = sum(all_avgs) / len(all_avgs)
        recent_avg = all_avgs[-1] if all_avgs else overall_avg
        trend = "improving" if len(all_avgs) > 1 and all_avgs[-1] > all_avgs[-2] else "steady"

        if overall_avg >= 80:
            level = "excellent"
        elif overall_avg >= 60:
            level = "good"
        elif overall_avg >= 40:
            level = "average"
        else:
            level = "struggling"

        return (
            f"Overall performance: {level} (avg score: {overall_avg:.0f}/100). "
            f"Most recent answer scored {recent_avg:.0f}/100. Trend: {trend}. "
            f"Questions answered: {len(all_avgs)}."
        )

    async def _prefetch_next_question(self, session: InterviewSession) -> None:
        """Speculatively generate the next question while the user reads/answers."""
        try:
            question = await self._generate_and_deliver_question(session)
            session.prefetched_question = question
            logger.debug(f"Pre-fetched question for interview {session.interview_id}")
        except Exception as e:
            logger.warning(f"Prefetch failed (non-critical): {e}")
            session.prefetched_question = None

    async def _load_or_create_session(self, interview_id: str) -> InterviewSession:
        """Load interview state from DB to reconstruct an InterviewSession."""
        async with async_session_factory() as db:
            interview = await interview_service.get_interview(db, interview_id)
            if interview is None:
                raise ValueError(f"Interview {interview_id} not found")

            role = interview.role
            if role is None:
                raise ValueError(f"Interview {interview_id} has no associated role")

            # Reconstruct turns from questions/responses
            turns: List[Dict[str, str]] = []
            topics_covered: List[str] = []
            all_scores: List[Dict[str, float]] = []
            primary_q_count = 0

            for q in interview.questions:
                turns.append({"role": "interviewer", "content": q.question_text})
                gen_ctx = q.generation_context or {}
                topic = gen_ctx.get("topic_area", "")
                if topic and topic not in topics_covered:
                    topics_covered.append(topic)

                if q.parent_question_id is None:
                    primary_q_count += 1

                if q.response:
                    r = q.response
                    turns.append({"role": "candidate", "content": r.response_text})
                    scores = {}
                    if r.score_relevance is not None:
                        scores = {
                            "relevance": r.score_relevance,
                            "depth": r.score_depth or 0,
                            "clarity": r.score_clarity or 0,
                            "communication": r.score_communication or 0,
                            "technical_accuracy": r.score_technical_accuracy or 0,
                        }
                    if scores:
                        all_scores.append(scores)

            # Build system prompt from template
            system_prompt = role.system_prompt_template.format(
                difficulty=interview.difficulty,
                interview_type=interview.interview_type,
                resume_context=interview.resume_text or "No resume provided",
                competencies=", ".join(role.competencies),
            )

            return InterviewSession(
                interview_id=interview_id,
                user_id=str(interview.user_id),
                role_slug=role.slug,
                role_display_name=role.display_name,
                system_prompt=system_prompt,
                difficulty=interview.difficulty,
                interview_type=interview.interview_type,
                competencies=role.competencies,
                turns=turns,
                topics_covered=topics_covered,
                primary_questions_asked=primary_q_count,
                all_scores=all_scores,
                total_tokens=0,
            )
