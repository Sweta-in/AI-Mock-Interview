"""
PrepAI — Tests for prompt template rendering.
Verifies prompts render correctly with sample inputs.
"""

import pytest
from apps.api.ai.prompts import (
    build_question_generation_prompt,
    build_evaluation_prompt,
    build_final_report_prompt,
    build_followup_prompt,
)


class TestQuestionGenerationPrompt:
    def test_renders_with_all_fields(self):
        messages = build_question_generation_prompt(
            role_slug="software-engineer-backend",
            interview_type="technical",
            difficulty="medium",
            topics_covered=["system_design"],
            questions_asked=3,
            remaining_turns=7,
            performance_summary="Overall: good (avg 72/100)",
            recent_context=[
                {"role": "interviewer", "content": "Describe a system you designed."},
                {"role": "candidate", "content": "I built a distributed cache using Redis."},
            ],
            competencies=["system_design", "api_design", "databases"],
            system_prompt="You are Alex Chen...",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Alex Chen" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "software-engineer-backend" in messages[1]["content"]
        assert "3" in messages[1]["content"]  # questions_asked
        assert "system_design" in messages[1]["content"]  # topic covered
        assert "api_design" in messages[1]["content"]  # remaining topic
        assert "JSON" in messages[1]["content"]  # output format instruction

    def test_renders_with_no_context(self):
        messages = build_question_generation_prompt(
            role_slug="product-manager",
            interview_type="behavioral",
            difficulty="easy",
            topics_covered=[],
            questions_asked=0,
            remaining_turns=10,
            performance_summary="No responses yet",
            recent_context=[],
            competencies=["product_strategy"],
            system_prompt="You are Jordan Park...",
        )

        assert len(messages) == 2
        assert "first question" in messages[1]["content"].lower() or "no prior context" in messages[1]["content"].lower()


class TestEvaluationPrompt:
    def test_renders_with_required_fields(self):
        messages = build_evaluation_prompt(
            question_text="Describe a time you optimized a database query.",
            expected_components=["query analysis", "indexing strategy", "performance measurement"],
            response_text="I once had a slow query on a users table. I added an index on the email column and response time dropped from 2s to 50ms.",
            recent_context=[
                {"role": "interviewer", "content": "Describe a time you optimized a database query."},
                {"role": "candidate", "content": "I once had a slow query..."},
            ],
            role="software-engineer-backend",
            difficulty="medium",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "MUST quote" in messages[0]["content"]
        assert "generic" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert "query analysis" in messages[1]["content"]
        assert "indexing strategy" in messages[1]["content"]
        assert "2s to 50ms" in messages[1]["content"]  # Candidate's actual answer
        assert "JSON" in messages[1]["content"]

    def test_anti_generic_instructions_present(self):
        messages = build_evaluation_prompt(
            question_text="Test question",
            expected_components=[],
            response_text="Test response",
            recent_context=[],
            role="test",
            difficulty="easy",
        )

        system_content = messages[0]["content"]
        # Must contain the exact anti-generic instruction
        assert "specific_strengths" in system_content
        assert "specific_weaknesses" in system_content
        assert "Never write generic feedback" in system_content or "generic" in system_content.lower()


class TestFinalReportPrompt:
    def test_renders_with_transcript(self):
        messages = build_final_report_prompt(
            transcript=[
                {"role": "interviewer", "content": "Tell me about your experience with APIs."},
                {"role": "candidate", "content": "I've built REST and gRPC APIs at scale."},
                {"role": "interviewer", "content": "What were the trade-offs?"},
                {"role": "candidate", "content": "REST is simpler but gRPC is better for internal services."},
            ],
            all_scores=[
                {"relevance": 70, "depth": 60, "clarity": 75, "communication": 80, "technical_accuracy": 65},
                {"relevance": 80, "depth": 75, "clarity": 80, "communication": 85, "technical_accuracy": 78},
            ],
            role="software-engineer-backend",
            interview_type="technical",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "software-engineer-backend" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "REST and gRPC" in messages[1]["content"]
        assert "JSON" in messages[1]["content"]
        assert "executive_summary" in messages[1]["content"]


class TestFollowupPrompt:
    def test_renders_followup(self):
        messages = build_followup_prompt(
            original_question="How would you design a rate limiter?",
            candidate_answer="I would use Redis to count requests.",
            followup_reason="vague",
            expected_components_missed=["sliding window algorithm", "distributed rate limiting"],
            system_prompt="You are Alex Chen...",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Redis" in messages[1]["content"]
        assert "sliding window" in messages[1]["content"]
        assert "vague" in messages[1]["content"]
        assert "ONE follow-up" in messages[1]["content"]

    def test_excellent_followup(self):
        messages = build_followup_prompt(
            original_question="Explain CAP theorem.",
            candidate_answer="CAP theorem states that in a distributed system you can only guarantee two of three: consistency, availability, and partition tolerance.",
            followup_reason="excellent",
            expected_components_missed=[],
            system_prompt="You are Alex Chen...",
        )

        assert "excellent" in messages[1]["content"].lower()
        assert "advanced" in messages[1]["content"].lower()
