"""
PrepAI — Guardrails for LLM output validation and retry logic.
Ensures evaluation responses are specific, non-generic, and well-structured.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from apps.api.ai.llm import LLMClient

logger = logging.getLogger(__name__)

# Phrases that indicate generic, low-quality feedback
GENERIC_PHRASES = [
    "more detail",
    "expand on",
    "great point",
    "well said",
    "good job",
    "needs improvement",
    "could be better",
    "well done",
    "good communication",
    "be more clear",
    "good answer",
    "nice work",
    "excellent response",
    "poor answer",
    "bad response",
    "decent answer",
    "satisfactory",
    "adequate response",
    "nice attempt",
]


async def validate_evaluation_response(response: dict) -> Tuple[bool, str]:
    """Validate an LLM evaluation response for quality and completeness.

    Returns (is_valid, rejection_reason).
    A response is invalid if:
    - Required fields are missing
    - Scores are not in 0-100 range
    - Strengths or weaknesses contain generic phrases
    - Strengths or weaknesses arrays are empty
    """
    # Check required top-level fields
    required_fields = [
        "scores", "specific_strengths", "specific_weaknesses",
        "should_followup", "followup_reason", "overall_assessment",
    ]
    for field in required_fields:
        if field not in response:
            return False, f"Missing required field: {field}"

    # Validate scores structure
    scores = response.get("scores", {})
    score_fields = ["relevance", "depth", "clarity", "communication", "technical_accuracy"]
    for sf in score_fields:
        if sf not in scores:
            return False, f"Missing score field: {sf}"
        score_val = scores[sf]
        if not isinstance(score_val, (int, float)):
            return False, f"Score '{sf}' must be numeric, got: {type(score_val).__name__}"
        if score_val < 0 or score_val > 100:
            return False, f"Score '{sf}' out of range (0-100): {score_val}"

    # Validate strengths are non-empty and non-generic
    strengths = response.get("specific_strengths", [])
    if not isinstance(strengths, list) or len(strengths) == 0:
        return False, "specific_strengths must be a non-empty array"

    for s in strengths:
        if not isinstance(s, str):
            return False, f"Each strength must be a string, got: {type(s).__name__}"
        lower = s.lower()
        for generic in GENERIC_PHRASES:
            if generic in lower and len(s) < 50:
                return False, (
                    f'Strength contains generic phrase "{generic}": "{s}". '
                    f"Rewrite with specific quotes from the candidate's answer."
                )

    # Validate weaknesses are non-empty and non-generic
    weaknesses = response.get("specific_weaknesses", [])
    if not isinstance(weaknesses, list) or len(weaknesses) == 0:
        return False, "specific_weaknesses must be a non-empty array"

    for w in weaknesses:
        if not isinstance(w, str):
            return False, f"Each weakness must be a string, got: {type(w).__name__}"
        lower = w.lower()
        for generic in GENERIC_PHRASES:
            if generic in lower and len(w) < 50:
                return False, (
                    f'Weakness contains generic phrase "{generic}": "{w}". '
                    f"Rewrite with specific quotes from the candidate's answer."
                )

    # Validate followup_reason enum
    valid_reasons = {"vague", "incomplete", "excellent", "none"}
    followup_reason = response.get("followup_reason", "")
    if followup_reason not in valid_reasons:
        return False, f"followup_reason must be one of {valid_reasons}, got: {followup_reason}"

    # Validate overall_assessment is present and substantive
    assessment = response.get("overall_assessment", "")
    if not isinstance(assessment, str) or len(assessment) < 20:
        return False, "overall_assessment must be a substantive sentence (min 20 chars)"

    return True, ""


async def evaluate_with_retry(
    messages: List[Dict[str, str]],
    llm: LLMClient,
    max_retries: int = 2,
    interview_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Call the LLM for evaluation and retry if guardrails reject the response.

    On rejection, appends feedback to the prompt explaining why the response
    was rejected and what needs to change.
    """
    current_messages = list(messages)  # Copy to avoid mutating original

    for attempt in range(max_retries + 1):
        result = await llm.complete_json(
            messages=current_messages,
            temperature=0.1,  # Low temperature for evaluation consistency
            max_tokens=2000,
            interview_id=interview_id,
        )

        parsed = result["parsed"]

        is_valid, rejection_reason = await validate_evaluation_response(parsed)

        if is_valid:
            return parsed

        logger.warning(
            f"Evaluation response rejected (attempt {attempt+1}/{max_retries+1}): "
            f"{rejection_reason}"
        )

        if attempt < max_retries:
            # Add rejection feedback to the conversation
            current_messages.append({
                "role": "assistant",
                "content": result["content"],
            })
            current_messages.append({
                "role": "user",
                "content": (
                    f"Your previous response was rejected because: {rejection_reason}\n\n"
                    f"Rewrite your evaluation with specific quotes from the candidate's answer. "
                    f"Every strength and weakness MUST reference something the candidate actually said. "
                    f"Do not use generic phrases like 'good communication' or 'needs more detail'."
                ),
            })

    # If all retries exhausted, return the last response with a warning
    logger.error(
        f"Evaluation guardrails failed after {max_retries+1} attempts. "
        f"Using last response despite validation failure."
    )
    return parsed
