"""Access Control List — Groups, Permissions, and the three association tables.

Resolution semantics (implemented in app.acl.resolver):

    * A user gets a permission if ANY of the following grant it:
        - their UserRole implies it (e.g. ADMIN always wins)
        - they are a member of a Group that has the permission
        - they have a direct UserPermission row with is_deny=False

    * An explicit UserPermission(is_deny=True) overrides every grant — this is
      the escape hatch for "revoke X from this one person even though they are
      in a group that normally has it".

Codename convention: `<app>.<resource>.<action>` (e.g. `sales.lead.create`).
Categories group codenames in the admin UI (e.g. "sales", "finance", "admin").
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Table, Column, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ── Association tables ────────────────────────────────────────────────────

user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", UUID(as_uuid=True), ForeignKey("acl_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

group_permissions = Table(
    "group_permissions",
    Base.metadata,
    Column("group_id", UUID(as_uuid=True), ForeignKey("acl_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("acl_permissions.id", ondelete="CASCADE"), primary_key=True),
)


# ── Core tables ───────────────────────────────────────────────────────────

class Permission(Base):
    __tablename__ = "acl_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codename: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Group(Base):
    __tablename__ = "acl_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    # Seeded groups are "system" — UI prevents deletion/rename but allows
    # permission tweaks. User-created groups are fully mutable.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPermission(Base):
    """Direct user → permission link. is_deny=True is an explicit revocation
    that wins over every other grant (role, group)."""

    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "permission_id", name="uq_user_permission"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("acl_permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_deny: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectMember(Base):
    """Per-project ACL — consulted when a permission carries `project_id`.

    A user's global permission grant (via role or group) still has to pair with
    membership in the specific project for the check to pass; otherwise the
    user can only see data for projects they actually belong to.
    """

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
