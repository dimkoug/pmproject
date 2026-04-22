"""First-run onboarding progress (#9).

One row per user — created on first /api/onboarding/status call. `steps_completed`
is a comma-separated list of step keys the user has ticked through. The wizard
shows as long as both `skipped_at` and `completed_at` are NULL.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"
    __table_args__ = (Index("ix_onboarding_user", "user_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    steps_completed: Mapped[str] = mapped_column(Text, default="", nullable=False)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
