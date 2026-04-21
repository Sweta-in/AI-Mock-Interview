"""
PrepAI — Answer evaluation logic.
Orchestrates LLM evaluation calls with guardrail validation.
"""

import logging
from typing import Dict, Any, Optional, List

from apps.api.ai.llm import LLMClient
from apps.api.ai.prompts import build_evaluation_prompt, build_final_report_prompt
from apps.api.ai.guardrails import validate_evaluation_response, evaluate_with_retry

logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates candidate answers using the LLM with guardrail validation."""

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or LLMClient()

    async def evaluate_answer(
        self,
        question_text: str,
        expected_components: List[str],
        response_text: str,
        recent_context: List[Dict[str, str]],
        role: str,
        difficulty: str,
        interview_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate a single answer with guardrail-validated retry.

        Returns the validated evaluation result dict.
        """
        messages = build_evaluation_prompt(
            question_text=question_text,
            expected_components=expected_components,
            response_text=response_text,
            recent_context=recent_context,
            role=role,
            difficulty=difficulty,
        )

        result = await evaluate_with_retry(
            messages=messages,
            llm=self.llm,
            max_retries=2,
            interview_id=interview_id,
        )

        return result

    async def generate_final_report(
        self,
        transcript: List[Dict[str, str]],
        all_scores: List[Dict[str, float]],
        role: str,
        interview_type: str,
        interview_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate the final interview report.

        Returns the parsed report dict.
        """
        messages = build_final_report_prompt(
            transcript=transcript,
            all_scores=all_scores,
            role=role,
            interview_type=interview_type,
        )

        result = await self.llm.complete_json(
            messages=messages,
            temperature=0.3,
            max_tokens=3000,
            interview_id=interview_id,
        )

        report = result["parsed"]

        # Validate required fields
        required_fields = [
            "executive_summary", "overall_score", "dimension_scores",
            "top_strengths", "top_improvements", "skill_breakdown",
            "recommended_next_steps", "comparison_benchmark",
        ]
        for field in required_fields:
            if field not in report:
                logger.warning(f"Final report missing field: {field}")
                report[field] = [] if field.startswith("top_") or field == "recommended_next_steps" else {}

        # Ensure overall_score is numeric
        if not isinstance(report.get("overall_score"), (int, float)):
            report["overall_score"] = 50.0

        return report
