"""
PrepAI — Production-ready prompt templates for all AI operations.
Each prompt includes role-specific vocabulary, structured output format,
and guardrail instructions.
"""

from typing import List, Dict, Optional


def build_question_generation_prompt(
    role_slug: str,
    interview_type: str,
    difficulty: str,
    topics_covered: List[str],
    questions_asked: int,
    remaining_turns: int,
    performance_summary: str,
    recent_context: List[Dict[str, str]],
    competencies: List[str],
    system_prompt: str,
) -> List[Dict[str, str]]:
    """Build the prompt for generating the next interview question.

    Returns a list of messages for the LLM.
    """
    # Format recent context as conversation turns
    context_str = ""
    if recent_context:
        context_str = "\n".join(
            f"{'Interviewer' if t['role'] == 'interviewer' else 'Candidate'}: {t['content']}"
            for t in recent_context[-6:]  # Last 6 turns
        )
    else:
        context_str = "(This is the first question — no prior context.)"

    topics_str = ", ".join(topics_covered) if topics_covered else "(none yet)"
    remaining_topics = [c for c in competencies if c not in topics_covered]
    remaining_topics_str = ", ".join(remaining_topics) if remaining_topics else "(all covered)"

    user_prompt = f"""Generate the next interview question based on the current session state.

## Session State
- **Role**: {role_slug}
- **Interview Type**: {interview_type}
- **Difficulty**: {difficulty}
- **Questions Asked So Far**: {questions_asked}
- **Remaining Turns**: {remaining_turns}
- **Topics Already Covered**: {topics_str}
- **Topics Not Yet Covered**: {remaining_topics_str}
- **Performance Summary**: {performance_summary}

## Recent Conversation Context (last 6 turns)
{context_str}

## Instructions
1. Select a topic from the uncovered areas if possible.
2. Calibrate difficulty to match the "{difficulty}" level.
3. If the candidate has been struggling, ask a slightly easier question to rebuild confidence.
4. If the candidate has been excelling, push toward advanced territory.
5. Do NOT repeat a topic already covered unless probing deeper based on a weak answer.
6. If this is the first question, start with a warm-up that's approachable but substantive.

## Required JSON Output Format
Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "question_text": "The exact question to ask the candidate",
    "question_type": "technical|behavioral|situational|system_design",
    "topic_area": "The specific competency area this question covers",
    "expected_components": ["Key point 1 a strong answer should include", "Key point 2", "Key point 3"],
    "difficulty": "easy|medium|hard",
    "followup_triggers": {{
        "if_vague": "Follow-up if answer is vague",
        "if_incomplete": "Follow-up if answer misses key components",
        "if_excellent": "Advanced follow-up if answer is outstanding"
    }}
}}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_evaluation_prompt(
    question_text: str,
    expected_components: List[str],
    response_text: str,
    recent_context: List[Dict[str, str]],
    role: str,
    difficulty: str,
) -> List[Dict[str, str]]:
    """Build the prompt for evaluating a candidate's answer.

    Temperature should be set to 0.1 for consistency.
    """
    context_str = ""
    if recent_context:
        context_str = "\n".join(
            f"{'Interviewer' if t['role'] == 'interviewer' else 'Candidate'}: {t['content']}"
            for t in recent_context[-3:]
        )
    else:
        context_str = "(No prior context)"

    components_str = "\n".join(f"  - {c}" for c in expected_components)

    system_prompt = f"""You are an expert interview evaluator for {role} roles at the {difficulty} level.

Your job is to evaluate the candidate's answer with extreme specificity and actionable feedback.

CRITICAL RULES:
1. Your specific_strengths and specific_weaknesses MUST quote or closely paraphrase specific phrases from the candidate's answer. Never write generic feedback like "good communication" or "needs more detail". If you cannot cite a specific phrase, do not include that bullet.
2. All scores are on a 0-100 scale where: 0-20 = Poor, 21-40 = Below Average, 41-60 = Average, 61-80 = Good, 81-100 = Excellent.
3. Your assessment must be calibrated to the {difficulty} difficulty level — what's "good" for a junior is "below average" for a senior.
4. Be honest and rigorous. Inflated scores help no one.
5. Never use these generic phrases: "more detail", "expand on", "great point", "well said", "good job", "needs improvement", "could be better", "well done", "good communication", "be more clear", "good answer"."""

    user_prompt = f"""## Question Asked
{question_text}

## Expected Components for a Strong Answer
{components_str}

## Candidate's Response
{response_text}

## Recent Conversation Context (last 3 turns)
{context_str}

## Required JSON Output Format
Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "scores": {{
        "relevance": <0-100>,
        "depth": <0-100>,
        "clarity": <0-100>,
        "communication": <0-100>,
        "technical_accuracy": <0-100>
    }},
    "components_covered": ["Which expected components the candidate addressed"],
    "components_missed": ["Which expected components the candidate missed"],
    "keywords_used": ["Relevant technical terms the candidate used correctly"],
    "keywords_missed": ["Important technical terms the candidate should have used"],
    "specific_strengths": [
        "Quote or closely paraphrase a specific phrase from the answer that demonstrates strength — e.g., 'The candidate correctly identified that \\"consistent hashing reduces rebalancing\\" which shows understanding of distributed systems'",
        "Another specific strength with a quote from the answer"
    ],
    "specific_weaknesses": [
        "Quote or paraphrase the specific weak area — e.g., 'When the candidate said \\"just use a database\\" they failed to consider trade-offs between SQL and NoSQL for this use case'",
        "Another specific weakness with a quote from the answer"
    ],
    "should_followup": true,
    "followup_reason": "vague|incomplete|excellent|none",
    "overall_assessment": "One concise sentence summarizing the candidate's performance on this question"
}}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_final_report_prompt(
    transcript: List[Dict[str, str]],
    all_scores: List[Dict[str, float]],
    role: str,
    interview_type: str,
) -> List[Dict[str, str]]:
    """Build the prompt for generating the final interview report."""

    # Format full transcript
    transcript_str = "\n\n".join(
        f"**{'Interviewer' if t['role'] == 'interviewer' else 'Candidate'}** (Turn {i+1}):\n{t['content']}"
        for i, t in enumerate(transcript)
    )

    # Format scores summary
    scores_str = ""
    if all_scores:
        for i, score_set in enumerate(all_scores):
            avg = sum(score_set.values()) / len(score_set) if score_set else 0
            scores_str += f"  Q{i+1}: avg={avg:.0f} ({', '.join(f'{k}={v:.0f}' for k, v in score_set.items())})\n"
    else:
        scores_str = "  (No scores available)"

    system_prompt = f"""You are a senior interview assessment specialist producing a comprehensive post-interview report for a {role} candidate ({interview_type} interview).

Your report must be:
1. Specific — cite exact moments from the interview, not generic observations.
2. Actionable — every improvement suggestion must include a concrete action step.
3. Calibrated — benchmark against typical candidates at the inferred level.
4. Balanced — acknowledge strengths before addressing weaknesses."""

    user_prompt = f"""## Full Interview Transcript
{transcript_str}

## Per-Question Scores
{scores_str}

## Required JSON Output Format
Respond with ONLY a JSON object:
{{
    "executive_summary": "A 3-4 sentence summary of the candidate's overall performance, highlighting their strongest and weakest areas with specific examples from the interview",
    "overall_score": <0-100 overall score>,
    "dimension_scores": {{
        "technical_knowledge": <0-100>,
        "problem_solving": <0-100>,
        "communication": <0-100>,
        "depth_of_understanding": <0-100>,
        "practical_experience": <0-100>
    }},
    "top_strengths": [
        "Specific strength 1 — cite a moment from the interview",
        "Specific strength 2 — cite a moment from the interview",
        "Specific strength 3 — cite a moment from the interview"
    ],
    "top_improvements": [
        "Specific improvement 1 — include a concrete action step (e.g., 'Practice system design problems focusing on database selection trade-offs. Use the DDIA book chapters 5-7.')",
        "Specific improvement 2 — include a concrete action step",
        "Specific improvement 3 — include a concrete action step"
    ],
    "skill_breakdown": {{
        "topic_area_1": {{
            "score": <0-100>,
            "summary": "One sentence assessment for this topic",
            "evidence": "Specific quote or paraphrase from the interview"
        }},
        "topic_area_2": {{
            "score": <0-100>,
            "summary": "...",
            "evidence": "..."
        }}
    }},
    "recommended_next_steps": [
        "Concrete next step 1 with specific resource or practice recommendation",
        "Concrete next step 2",
        "Concrete next step 3"
    ],
    "comparison_benchmark": "entry|mid|senior|staff"
}}"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_followup_prompt(
    original_question: str,
    candidate_answer: str,
    followup_reason: str,
    expected_components_missed: List[str],
    system_prompt: str,
) -> List[Dict[str, str]]:
    """Build the prompt for generating a follow-up question.

    Returns a single follow-up question text (string, not JSON).
    """
    missed_str = "\n".join(f"  - {c}" for c in expected_components_missed) if expected_components_missed else "  (none specified)"

    reason_instructions = {
        "vague": "The candidate's answer was vague and lacked specifics. Ask a targeted follow-up that requires them to provide a concrete example, specific technology, or exact numbers.",
        "incomplete": "The candidate missed key components of a complete answer. Ask about the most important missing component directly.",
        "excellent": "The candidate gave an excellent answer. Push them further with an advanced related question that tests the limits of their knowledge.",
    }

    instruction = reason_instructions.get(
        followup_reason,
        "Ask a relevant follow-up based on the candidate's answer."
    )

    user_prompt = f"""## Original Question
{original_question}

## Candidate's Answer
{candidate_answer}

## Follow-up Reason: {followup_reason}
{instruction}

## Missing Components
{missed_str}

## Instructions
Generate exactly ONE follow-up question. Do NOT include any preamble, explanation, or JSON formatting.
Just output the follow-up question text directly. Keep it to 1-2 sentences.
Do NOT say things like "That's a great point" or "Good answer" — go directly to the follow-up question."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
