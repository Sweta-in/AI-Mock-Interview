"""
PrepAI — Unit tests for InterviewEngine.
Tests question generation, follow-up logic, session completion, and timeout handling.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from apps.api.interview.engine import (
    InterviewEngine,
    InterviewSession,
    Question,
    ResponseData,
    EvalResult,
)


@pytest.fixture
def mock_sio():
    sio = AsyncMock()
    sio.emit = AsyncMock()
    return sio


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.complete_json = AsyncMock(return_value={
        "content": '{}',
        "parsed": {
            "question_text": "Tell me about a time you designed a distributed system.",
            "question_type": "technical",
            "topic_area": "system_design",
            "expected_components": ["scalability", "trade-offs", "data consistency"],
            "difficulty": "medium",
            "followup_triggers": {
                "if_vague": "Can you be more specific about the architecture?",
                "if_incomplete": "What about data consistency?",
                "if_excellent": "How would you handle multi-region failover?",
            },
        },
        "model_used": "anthropic/claude-sonnet-4-20250514",
        "prompt_tokens": 500,
        "completion_tokens": 200,
        "cost_usd": 0.0045,
        "latency_ms": 1200,
    })
    llm.complete = AsyncMock(return_value={
        "content": "Can you walk me through the specific implementation details?",
        "model_used": "anthropic/claude-sonnet-4-20250514",
        "prompt_tokens": 300,
        "completion_tokens": 50,
        "cost_usd": 0.002,
        "latency_ms": 800,
    })
    return llm


@pytest.fixture
def mock_evaluator():
    evaluator = AsyncMock()
    evaluator.evaluate_answer = AsyncMock(return_value={
        "scores": {
            "relevance": 75,
            "depth": 65,
            "clarity": 80,
            "communication": 70,
            "technical_accuracy": 72,
        },
        "should_followup": False,
        "followup_reason": "none",
        "specific_strengths": [
            'The candidate correctly identified "consistent hashing" as a solution',
        ],
        "specific_weaknesses": [
            'When mentioning "just use Redis" the candidate missed cache invalidation concerns',
        ],
        "components_covered": ["scalability"],
        "components_missed": ["data consistency", "trade-offs"],
        "keywords_used": ["consistent hashing", "sharding"],
        "keywords_missed": ["CAP theorem", "eventual consistency"],
        "overall_assessment": "Solid understanding of basics but lacks depth in consistency models.",
    })
    evaluator.generate_final_report = AsyncMock(return_value={
        "executive_summary": "The candidate demonstrated solid foundational knowledge.",
        "overall_score": 72,
        "dimension_scores": {
            "technical_knowledge": 70,
            "problem_solving": 68,
            "communication": 78,
            "depth_of_understanding": 65,
            "practical_experience": 72,
        },
        "top_strengths": ["Strong system design fundamentals", "Clear communication", "Good examples"],
        "top_improvements": ["Deepen consistency model knowledge", "Practice trade-off analysis", "Cover edge cases"],
        "skill_breakdown": {
            "system_design": {"score": 72, "summary": "Good fundamentals"},
            "algorithms": {"score": 65, "summary": "Needs practice"},
        },
        "recommended_next_steps": ["Read DDIA chapters 5-7", "Practice system design problems"],
        "comparison_benchmark": "mid",
    })
    return evaluator


@pytest.fixture
def sample_session():
    return InterviewSession(
        interview_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        role_slug="software-engineer-backend",
        role_display_name="Backend Engineer",
        system_prompt="You are Alex Chen, a Senior Staff Engineer...",
        difficulty="medium",
        interview_type="technical",
        competencies=["system_design", "api_design", "databases"],
        turns=[],
        topics_covered=[],
        primary_questions_asked=0,
        all_scores=[],
    )


class TestInterviewEngine:
    """Tests for the InterviewEngine class."""

    def test_engine_initialization(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        assert engine.MAX_QUESTIONS == 10
        assert engine.MAX_FOLLOWUPS_PER_QUESTION == 2
        assert engine.ANSWER_TIMEOUT_SECONDS == 300

    def test_performance_signal_no_scores(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
        )
        signal = engine._get_performance_signal(session)
        assert "No responses yet" in signal

    def test_performance_signal_with_scores(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
            all_scores=[
                {"relevance": 80, "depth": 70, "clarity": 85, "communication": 75, "technical_accuracy": 90},
                {"relevance": 85, "depth": 75, "clarity": 80, "communication": 80, "technical_accuracy": 85},
            ],
        )
        signal = engine._get_performance_signal(session)
        assert "good" in signal or "excellent" in signal
        assert "Questions answered: 2" in signal

    def test_performance_signal_struggling(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="hard",
            interview_type="technical",
            competencies=[],
            all_scores=[
                {"relevance": 20, "depth": 15, "clarity": 25, "communication": 30, "technical_accuracy": 10},
            ],
        )
        signal = engine._get_performance_signal(session)
        assert "struggling" in signal

    @pytest.mark.asyncio
    async def test_determine_followup_max_reached(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
            followups_for_current=2,  # Max reached
        )
        eval_result = EvalResult(
            scores={"relevance": 40},
            should_followup=True,
            followup_reason="vague",
            specific_strengths=[],
            specific_weaknesses=[],
            components_missed=[],
            raw={},
        )
        result = await engine._determine_followup(eval_result, session)
        assert result is False

    @pytest.mark.asyncio
    async def test_determine_followup_not_needed(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
            followups_for_current=0,
        )
        eval_result = EvalResult(
            scores={"relevance": 80},
            should_followup=False,
            followup_reason="none",
            specific_strengths=[],
            specific_weaknesses=[],
            components_missed=[],
            raw={},
        )
        result = await engine._determine_followup(eval_result, session)
        assert result is False

    @pytest.mark.asyncio
    async def test_determine_followup_vague_answer(self, mock_sio, mock_llm, mock_evaluator):
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
            followups_for_current=0,
            primary_questions_asked=3,
        )
        eval_result = EvalResult(
            scores={"relevance": 40},
            should_followup=True,
            followup_reason="vague",
            specific_strengths=[],
            specific_weaknesses=[],
            components_missed=["data consistency"],
            raw={},
        )
        result = await engine._determine_followup(eval_result, session)
        assert result is True

    @pytest.mark.asyncio
    async def test_determine_followup_low_remaining(self, mock_sio, mock_llm, mock_evaluator):
        """Don't follow up if running low on questions (unless vague)."""
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
            followups_for_current=0,
            primary_questions_asked=9,  # Only 1 remaining
        )
        # Non-vague followup should be skipped when running low
        eval_result = EvalResult(
            scores={"relevance": 60},
            should_followup=True,
            followup_reason="incomplete",
            specific_strengths=[],
            specific_weaknesses=[],
            components_missed=[],
            raw={},
        )
        result = await engine._determine_followup(eval_result, session)
        assert result is False

    @pytest.mark.asyncio
    async def test_evaluate_response_no_current_question(self, mock_sio, mock_llm, mock_evaluator):
        """Fallback scores when there's no current question context."""
        engine = InterviewEngine(sio=mock_sio, llm=mock_llm, evaluator=mock_evaluator)
        session = InterviewSession(
            interview_id="test",
            user_id="user",
            role_slug="backend",
            role_display_name="Backend",
            system_prompt="...",
            difficulty="medium",
            interview_type="technical",
            competencies=[],
            current_question=None,
        )
        response = ResponseData(
            question_id="q1",
            response_text="Some answer",
            response_time_seconds=30.0,
        )
        result = await engine._evaluate_response(session, response)
        assert result.scores["relevance"] == 50  # Fallback score
        assert result.should_followup is False
