"""Initial schema — all PrepAI tables

Revision ID: 001_initial_schema
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ───────────────────────────────────────────────────────
    user_plan = sa.Enum("free", "pro", name="user_plan")
    user_plan.create(op.get_bind(), checkfirst=True)

    interview_status = sa.Enum(
        "created", "active", "completed", "abandoned", "error",
        name="interview_status",
    )
    interview_status.create(op.get_bind(), checkfirst=True)

    interview_difficulty = sa.Enum("easy", "medium", "hard", name="interview_difficulty")
    interview_difficulty.create(op.get_bind(), checkfirst=True)

    interview_type_enum = sa.Enum(
        "technical", "behavioral", "mixed",
        name="interview_type_enum",
    )
    interview_type_enum.create(op.get_bind(), checkfirst=True)

    question_type_enum = sa.Enum(
        "technical", "behavioral", "situational", "followup", "system_design",
        name="question_type_enum",
    )
    question_type_enum.create(op.get_bind(), checkfirst=True)

    feedback_level_enum = sa.Enum("answer", "session", name="feedback_level_enum")
    feedback_level_enum.create(op.get_bind(), checkfirst=True)

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("supabase_id", sa.String(255), unique=True, nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("plan", user_plan, nullable=False, server_default="free"),
        sa.Column("interviews_used_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_supabase_id", "users", ["supabase_id"])

    # ── interview_roles ──────────────────────────────────────────────────
    op.create_table(
        "interview_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("competencies", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("system_prompt_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_interview_roles_slug", "interview_roles", ["slug"])

    # ── interviews ───────────────────────────────────────────────────────
    op.create_table(
        "interviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("interview_roles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_token", sa.String(255), unique=True, nullable=False),
        sa.Column("status", interview_status, nullable=False, server_default="created"),
        sa.Column("difficulty", interview_difficulty, nullable=False, server_default="medium"),
        sa.Column("interview_type", interview_type_enum, nullable=False, server_default="mixed"),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("technical_score", sa.Float(), nullable=True),
        sa.Column("behavioral_score", sa.Float(), nullable=True),
        sa.Column("communication_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_interviews_user_id", "interviews", ["user_id"])
    op.create_index("ix_interviews_status", "interviews", ["status"])
    op.create_index("ix_interviews_session_token", "interviews", ["session_token"], unique=True)

    # ── interview_questions ──────────────────────────────────────────────
    op.create_table(
        "interview_questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("interview_id", UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_num", sa.Integer(), nullable=False),
        sa.Column("question_type", question_type_enum, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("parent_question_id", UUID(as_uuid=True), sa.ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generation_context", JSONB, nullable=True),
        sa.Column("asked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_interview_questions_interview_seq", "interview_questions", ["interview_id", "sequence_num"])

    # ── interview_responses ──────────────────────────────────────────────
    op.create_table(
        "interview_responses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", UUID(as_uuid=True), sa.ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interview_id", UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("input_mode", sa.String(50), nullable=False, server_default="text"),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("response_time_seconds", sa.Float(), nullable=True),
        sa.Column("score_relevance", sa.Float(), nullable=True),
        sa.Column("score_depth", sa.Float(), nullable=True),
        sa.Column("score_clarity", sa.Float(), nullable=True),
        sa.Column("score_communication", sa.Float(), nullable=True),
        sa.Column("score_technical_accuracy", sa.Float(), nullable=True),
    )
    op.create_index("ix_interview_responses_interview_id", "interview_responses", ["interview_id"])

    # ── feedback_items ───────────────────────────────────────────────────
    op.create_table(
        "feedback_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("interview_id", UUID(as_uuid=True), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_id", UUID(as_uuid=True), sa.ForeignKey("interview_responses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feedback_level", feedback_level_enum, nullable=False, server_default="answer"),
        sa.Column("strengths", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("weaknesses", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("improvements", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("example_answer", sa.Text(), nullable=True),
        sa.Column("keywords_used", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("keywords_missed", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("raw_llm_output", JSONB, nullable=True),
    )

    # ── user_skill_snapshots ─────────────────────────────────────────────
    op.create_table(
        "user_skill_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("interview_roles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("skill_scores", JSONB, nullable=False, server_default="{}"),
        sa.Column("interviews_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id", "role_id", "snapshot_date", name="uq_user_role_date"),
    )


def downgrade() -> None:
    op.drop_table("user_skill_snapshots")
    op.drop_table("feedback_items")
    op.drop_table("interview_responses")
    op.drop_table("interview_questions")
    op.drop_table("interviews")
    op.drop_table("interview_roles")
    op.drop_table("users")

    # Drop enum types
    sa.Enum(name="feedback_level_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="question_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interview_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interview_difficulty").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interview_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_plan").drop(op.get_bind(), checkfirst=True)
