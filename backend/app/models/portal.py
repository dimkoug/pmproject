"""Customer portal — magic-link tokens (#74).

A `PortalToken` is a one-time URL fragment that an admin sends to a customer.
The customer clicks the link, the backend swaps it for a short-lived portal
JWT scoped to the company, and the customer can browse their invoices /
pay them via Stripe.

Tokens are single-use: `used_at` is stamped on the first successful exchange.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortalToken(Base):
    __tablename__ = "portal_tokens"
    __table_args__ = (
        Index("ix_portal_tokens_token", "token", unique=True),
        Index("ix_portal_tokens_company", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_companies.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
