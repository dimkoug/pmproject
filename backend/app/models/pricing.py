"""Pricing rules + returns/refunds (#2, #3).

Kept in its own module so erp.py doesn't balloon further. Imported from
`app.models.pricing` by the pricing router and the migration runner picks
up the new tables via Base.metadata.create_all.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ── Pricing rules ──────────────────────────────────────────────────


class DiscountType(str, enum.Enum):
    PERCENT = "percent"     # e.g. 10 means 10% off
    AMOUNT = "amount"       # fixed currency amount off


class PriceList(Base):
    """Named price list (e.g. 'Wholesale', 'Retail', 'VIP'). A product can
    have one price per list — look it up via PriceListItem."""
    __tablename__ = "pricing_lists"
    __table_args__ = (Index("ix_pricing_lists_name", "name", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceListItem(Base):
    __tablename__ = "pricing_list_items"
    __table_args__ = (
        # Unique per (list, product, tier) — one row per quantity tier for a
        # product in a given price list. Omitting min_quantity here would
        # block tier pricing entirely.
        Index("ix_pli_list_product_tier", "price_list_id", "product_id", "min_quantity", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pricing_lists.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    # If set, the unit_price kicks in at this quantity threshold; the next
    # higher-min_quantity row wins above it. Cheap tier pricing.
    min_quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class DiscountRule(Base):
    """Coupon code OR auto-apply rule. When `code` is NULL the rule applies
    automatically if min_subtotal is met. When `code` is set it only kicks
    in when the customer provides that code at checkout."""
    __tablename__ = "pricing_discounts"
    __table_args__ = (
        Index("ix_pricing_discounts_code", "code"),
        Index("ix_pricing_discounts_active_window", "starts_at", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(60))
    discount_type: Mapped[DiscountType] = mapped_column(Enum(DiscountType), default=DiscountType.PERCENT)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    min_subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_redemptions: Mapped[int | None] = mapped_column(Integer)
    redemptions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Returns / Refunds ──────────────────────────────────────────────


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    RECEIVED = "received"
    REFUNDED = "refunded"
    REJECTED = "rejected"


class ReturnMerchandise(Base):
    """Return Merchandise Authorization (RMA). One per customer return.
    Line items link to the original invoice items being returned."""
    __tablename__ = "erp_returns"
    __table_args__ = (
        Index("ix_erp_returns_invoice", "invoice_id"),
        Index("ix_erp_returns_rma", "rma_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id"), nullable=False)
    rma_number: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReturnStatus] = mapped_column(Enum(ReturnStatus), default=ReturnStatus.REQUESTED)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReturnLine(Base):
    __tablename__ = "erp_return_lines"
    __table_args__ = (Index("ix_erp_return_lines_return", "return_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_returns.id", ondelete="CASCADE"), nullable=False)
    invoice_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoice_items.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
