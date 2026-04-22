"""Automation rules — IFTTT-style: when an event fires, evaluate conditions on
the event payload, then execute a list of actions.

Trigger events are emitted by `app.services.audit.log_audit` (and via direct
calls to `app.services.automation.fire_event`). The catalog of supported
events lives in `app.services.automation.SUPPORTED_EVENTS`.

Conditions and actions are stored as JSON for flexibility — the evaluator
interprets them.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# Portable JSON column: JSONB on Postgres, plain JSON on others (sqlite for tests).
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    __table_args__ = (
        Index("ix_automation_rules_event", "trigger_event"),
        Index("ix_automation_rules_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trigger_event: Mapped[str] = mapped_column(String(80), nullable=False)
    conditions: Mapped[list | None] = mapped_column(PortableJSON, default=list, server_default="[]")
    actions: Mapped[list] = mapped_column(PortableJSON, default=list, server_default="[]", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomationRuleRun(Base):
    __tablename__ = "automation_rule_runs"
    __table_args__ = (
        Index("ix_automation_runs_rule", "rule_id"),
        Index("ix_automation_runs_at", "triggered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict | None] = mapped_column(PortableJSON)
    actions_run: Mapped[int] = mapped_column(Integer, default=0)
    actions_failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="success")  # success | partial | failed | skipped
    error: Mapped[str | None] = mapped_column(Text)
