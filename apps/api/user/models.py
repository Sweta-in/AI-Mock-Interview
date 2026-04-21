"""
PrepAI — User SQLAlchemy models.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from apps.api.db.postgres import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(320), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False, default="")
    plan = Column(
        SAEnum("free", "pro", name="user_plan", create_type=True),
        nullable=False,
        default="free",
    )
    interviews_used_this_month = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    interviews = relationship("Interview", back_populates="user", lazy="selectin")
    skill_snapshots = relationship("UserSkillSnapshot", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User {self.email} plan={self.plan}>"
