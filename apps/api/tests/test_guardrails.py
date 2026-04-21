"""
PrepAI — Unit tests for guardrails validation.
Tests generic phrase detection, missing fields, out-of-range scores.
"""

import pytest
from apps.api.ai.guardrails import validate_evaluation_response, GENERIC_PHRASES


class TestValidateEvaluationResponse:
    """Tests for validate_evaluation_response."""

    @pytest.mark.asyncio
    async def test_valid_response_passes(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "components_covered": ["scalability"],
            "components_missed": ["data consistency"],
            "keywords_used": ["sharding"],
            "keywords_missed": ["CAP theorem"],
            "specific_strengths": [
                'The candidate correctly identified "consistent hashing reduces rebalancing" which shows understanding of distributed systems',
            ],
            "specific_weaknesses": [
                'When the candidate said "just use a database" they failed to consider trade-offs between SQL and NoSQL for this use case',
            ],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Solid understanding of distributed systems fundamentals with room for improvement in consistency models.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is True
        assert reason == ""

    @pytest.mark.asyncio
    async def test_missing_required_field(self):
        response = {
            "scores": {"relevance": 75, "depth": 65, "clarity": 80, "communication": 70, "technical_accuracy": 72},
            "specific_strengths": ["Good point about caching"],
            # Missing: specific_weaknesses, should_followup, followup_reason, overall_assessment
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "Missing required field" in reason

    @pytest.mark.asyncio
    async def test_missing_score_field(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                # Missing: clarity, communication, technical_accuracy
            },
            "specific_strengths": ["Using quotes from the actual answer about system design"],
            "specific_weaknesses": ["The candidate's statement about 'NoSQL is always better' shows a gap"],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Needs improvement in database selection rationale.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "Missing score field" in reason

    @pytest.mark.asyncio
    async def test_score_out_of_range_high(self):
        response = {
            "scores": {
                "relevance": 150,  # Out of range!
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": ["Candidate explained 'event sourcing well' in the context of audit logging"],
            "specific_weaknesses": ["Missed the point about 'CQRS separation of read/write models'"],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Good understanding but score was inflated for relevance.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "out of range" in reason

    @pytest.mark.asyncio
    async def test_score_out_of_range_negative(self):
        response = {
            "scores": {
                "relevance": -10,  # Negative!
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": ["Mentioned 'distributed tracing' which is relevant"],
            "specific_weaknesses": ["Said 'monolith is bad' without nuance about trade-offs"],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Below average performance on this question.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "out of range" in reason

    @pytest.mark.asyncio
    async def test_generic_phrase_in_strengths(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": [
                "good job",  # Generic! And short enough to trigger
            ],
            "specific_weaknesses": [
                'When discussing caching, the candidate said "just add Redis" without considering cache invalidation strategies',
            ],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Average performance with some generic reasoning.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "generic phrase" in reason.lower()

    @pytest.mark.asyncio
    async def test_generic_phrase_in_weaknesses(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": [
                'Candidate correctly described "eventual consistency" in the context of distributed databases',
            ],
            "specific_weaknesses": [
                "needs improvement",  # Generic! Short enough to trigger
            ],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Reasonable but incomplete answer on database design.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "generic phrase" in reason.lower()

    @pytest.mark.asyncio
    async def test_empty_strengths_array(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": [],  # Empty!
            "specific_weaknesses": [
                'The candidate said "I would use microservices" without discussing the complexity trade-offs',
            ],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Answer lacked specific technical depth.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "non-empty" in reason

    @pytest.mark.asyncio
    async def test_empty_weaknesses_array(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": [
                'Candidate demonstrated deep knowledge by explaining "write-ahead logging for crash recovery"',
            ],
            "specific_weaknesses": [],  # Empty!
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "Strong answer with clear technical depth.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "non-empty" in reason

    @pytest.mark.asyncio
    async def test_invalid_followup_reason(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": [
                'Mentioned "load balancing with health checks" which is a practical consideration',
            ],
            "specific_weaknesses": [
                'The candidate\'s approach to "scaling the database" missed read replicas entirely',
            ],
            "should_followup": True,
            "followup_reason": "invalid_reason",  # Bad enum!
            "overall_assessment": "Reasonable answer but missed scaling strategies.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "followup_reason" in reason

    @pytest.mark.asyncio
    async def test_short_overall_assessment(self):
        response = {
            "scores": {
                "relevance": 75,
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": [
                'Good use of the term "idempotency" when discussing API design patterns',
            ],
            "specific_weaknesses": [
                'Said "REST is better than gRPC" without considering the use case requirements',
            ],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "OK",  # Too short!
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "overall_assessment" in reason

    @pytest.mark.asyncio
    async def test_non_numeric_score(self):
        response = {
            "scores": {
                "relevance": "high",  # Not numeric!
                "depth": 65,
                "clarity": 80,
                "communication": 70,
                "technical_accuracy": 72,
            },
            "specific_strengths": ["Valid strength with quote from answer"],
            "specific_weaknesses": ["Valid weakness with quote from answer"],
            "should_followup": False,
            "followup_reason": "none",
            "overall_assessment": "This is a sufficiently long assessment for testing purposes.",
        }
        is_valid, reason = await validate_evaluation_response(response)
        assert is_valid is False
        assert "numeric" in reason

    @pytest.mark.asyncio
    async def test_all_generic_phrases_detected(self):
        """Verify all phrases in GENERIC_PHRASES are actually checked."""
        for phrase in GENERIC_PHRASES:
            response = {
                "scores": {
                    "relevance": 75, "depth": 65, "clarity": 80,
                    "communication": 70, "technical_accuracy": 72,
                },
                "specific_strengths": [phrase],  # Short generic
                "specific_weaknesses": ["Valid weakness about specific quote from candidate's answer"],
                "should_followup": False,
                "followup_reason": "none",
                "overall_assessment": "This is a sufficiently long assessment for testing purposes.",
            }
            is_valid, reason = await validate_evaluation_response(response)
            assert is_valid is False, f"Generic phrase not caught: '{phrase}'"
