import uuid
from datetime import datetime
import enum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ── Chart of Accounts ───────────────────────────────────────────────

class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class Account(Base):
    __tablename__ = "erp_accounts"
    __table_args__ = (Index("ix_erp_accounts_code", "code", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Vendors ─────────────────────────────────────────────────────────

class Vendor(Base):
    __tablename__ = "erp_vendors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(50))
    payment_terms: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Invoices ────────────────────────────────────────────────────────

class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class InvoiceType(str, enum.Enum):
    RECEIVABLE = "receivable"
    PAYABLE = "payable"


class Invoice(Base):
    __tablename__ = "erp_invoices"
    __table_args__ = (
        Index("ix_erp_invoices_project", "project_id"),
        Index("ix_erp_invoices_status", "status"),
        Index("ix_erp_invoices_number", "invoice_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_vendors.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_companies.id"))
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), default=InvoiceType.RECEIVABLE)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    fx_rate: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text)
    stripe_session_id: Mapped[str | None] = mapped_column(String(120))
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(120))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceItem(Base):
    __tablename__ = "erp_invoice_items"
    __table_args__ = (Index("ix_erp_invoice_items_invoice", "invoice_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)


# ── Expenses ────────────────────────────────────────────────────────

class ExpenseCategory(str, enum.Enum):
    LABOR = "labor"
    MATERIALS = "materials"
    EQUIPMENT = "equipment"
    TRAVEL = "travel"
    SOFTWARE = "software"
    CONSULTING = "consulting"
    OVERHEAD = "overhead"
    OTHER = "other"


class Expense(Base):
    __tablename__ = "erp_expenses"
    __table_args__ = (
        Index("ix_erp_expenses_project", "project_id"),
        Index("ix_erp_expenses_date", "expense_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_vendors.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory), default=ExpenseCategory.OTHER)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    fx_rate: Mapped[float] = mapped_column(Float, default=1.0)
    expense_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    receipt_ref: Mapped[str | None] = mapped_column(String(255))
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Purchase Orders ─────────────────────────────────────────────────

class POStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrder(Base):
    __tablename__ = "erp_purchase_orders"
    __table_args__ = (
        Index("ix_erp_po_project", "project_id"),
        Index("ix_erp_po_vendor", "vendor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_vendors.id"), nullable=False)
    po_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[POStatus] = mapped_column(Enum(POStatus), default=POStatus.DRAFT)
    description: Mapped[str | None] = mapped_column(Text)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    order_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Vendor performance tracking (#4) — set by the GRN / receiving flow.
    received_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 0..1: fraction of received lines flagged defective by QC.
    defect_rate: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseOrderLine(Base):
    __tablename__ = "erp_purchase_order_lines"
    __table_args__ = (Index("ix_erp_po_lines_po", "po_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_received: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)


# ── Assets ──────────────────────────────────────────────────────────

class AssetStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    DISPOSED = "disposed"


class Asset(Base):
    __tablename__ = "erp_assets"
    __table_args__ = (Index("ix_erp_assets_project", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_tag: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.ACTIVE)
    purchase_cost: Mapped[float | None] = mapped_column(Float)
    current_value: Mapped[float | None] = mapped_column(Float)
    purchase_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Budgets ─────────────────────────────────────────────────────────

class Budget(Base):
    __tablename__ = "erp_budgets"
    __table_args__ = (Index("ix_erp_budgets_project", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BudgetLine(Base):
    __tablename__ = "erp_budget_lines"
    __table_args__ = (Index("ix_erp_budget_lines_budget", "budget_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_budgets.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_accounts.id"))
    category: Mapped[ExpenseCategory | None] = mapped_column(Enum(ExpenseCategory))
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    planned_amount: Mapped[float] = mapped_column(Float, default=0.0)


# ── Currencies & FX ─────────────────────────────────────────────────

class Currency(Base):
    __tablename__ = "erp_currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(8))


class FxRate(Base):
    __tablename__ = "erp_fx_rates"
    __table_args__ = (Index("ix_erp_fx_date", "rate_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_code: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_code: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    rate_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Payments & Aging ────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "erp_payments"
    __table_args__ = (Index("ix_erp_payments_invoice", "invoice_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    method: Mapped[str | None] = mapped_column(String(50))
    reference: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Recurring Invoices ──────────────────────────────────────────────

class RecurringFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RecurringInvoice(Base):
    __tablename__ = "erp_recurring_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_vendors.id"))
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), default=InvoiceType.RECEIVABLE)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[RecurringFrequency] = mapped_column(Enum(RecurringFrequency), default=RecurringFrequency.MONTHLY)
    next_run: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_generated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Journal Entries (General Ledger) ────────────────────────────────

class JournalEntry(Base):
    __tablename__ = "erp_journal_entries"
    __table_args__ = (Index("ix_erp_je_date", "entry_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memo: Mapped[str | None] = mapped_column(Text)
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalLine(Base):
    __tablename__ = "erp_journal_lines"
    __table_args__ = (Index("ix_erp_jl_entry", "entry_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_journal_entries.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_accounts.id"), nullable=False)
    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str | None] = mapped_column(String(500))
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_cost_centers.id"))
    profit_center_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_profit_centers.id"))


class CostCenter(Base):
    __tablename__ = "erp_cost_centers"
    __table_args__ = (Index("ix_erp_cc_code", "code", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfitCenter(Base):
    __tablename__ = "erp_profit_centers"
    __table_args__ = (Index("ix_erp_pc_code", "code", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Bank Reconciliation ─────────────────────────────────────────────

class BankTransaction(Base):
    __tablename__ = "erp_bank_transactions"
    __table_args__ = (Index("ix_erp_bank_date", "txn_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_accounts.id"))
    txn_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255))
    matched_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id"))
    matched_expense_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_expenses.id"))
    matched_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_journal_entries.id"))
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Inventory ───────────────────────────────────────────────────────

class Warehouse(Base):
    __tablename__ = "erp_warehouses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "erp_products"
    __table_args__ = (
        Index("ix_erp_products_sku", "sku", unique=True),
        Index("ix_erp_products_barcode", "barcode", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    # Scanner-friendly barcode (EAN-13 / UPC-A / Code128). Unique so scans
    # resolve to exactly one product — pair with a lookup endpoint.
    barcode: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    reorder_qty: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    track_batch: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    track_serial: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WarehouseBin(Base):
    """Physical bin/location inside a warehouse (e.g. "A-12-03"). A
    StockMovement can record which bin material went to or came from so
    pickers know where to look without re-surveying the warehouse."""
    __tablename__ = "erp_warehouse_bins"
    __table_args__ = (
        Index("ix_erp_bins_wh_code", "warehouse_id", "code", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_warehouses.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MovementType(str, enum.Enum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER = "transfer"
    ADJUST = "adjust"


class StockMovement(Base):
    __tablename__ = "erp_stock_movements"
    __table_args__ = (
        Index("ix_erp_stock_product", "product_id"),
        Index("ix_erp_stock_date", "movement_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_warehouses.id"), nullable=False)
    bin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_warehouse_bins.id"))
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Float)
    reference: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_stock_batches.id"))
    serial_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_stock_serials.id"))
    movement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Asset Depreciation ──────────────────────────────────────────────

class DepreciationMethod(str, enum.Enum):
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"


class DepreciationSchedule(Base):
    __tablename__ = "erp_depreciation_schedules"
    __table_args__ = (Index("ix_erp_dep_asset", "asset_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_assets.id"), nullable=False)
    method: Mapped[DepreciationMethod] = mapped_column(Enum(DepreciationMethod), default=DepreciationMethod.STRAIGHT_LINE)
    useful_life_months: Mapped[int] = mapped_column(Integer, nullable=False)
    salvage_value: Mapped[float] = mapped_column(Float, default=0.0)
    rate: Mapped[float | None] = mapped_column(Float)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accumulated: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Credit Notes ────────────────────────────────────────────────────

class CreditNote(Base):
    __tablename__ = "erp_credit_notes"
    __table_args__ = (Index("ix_erp_cn_invoice", "invoice_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id"), nullable=False)
    cn_number: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    issued_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Purchase Requisitions ───────────────────────────────────────────

class RequisitionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"


class Requisition(Base):
    __tablename__ = "erp_requisitions"
    __table_args__ = (Index("ix_erp_req_project", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    requester_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    req_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[RequisitionStatus] = mapped_column(Enum(RequisitionStatus), default=RequisitionStatus.DRAFT)
    justification: Mapped[str | None] = mapped_column(Text)
    estimated_amount: Mapped[float] = mapped_column(Float, default=0.0)
    needed_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_po_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_purchase_orders.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RequisitionItem(Base):
    __tablename__ = "erp_requisition_items"
    __table_args__ = (Index("ix_erp_req_item_req", "req_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_requisitions.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)


# ── Sales Orders (Quote → SO → Invoice) ─────────────────────────────

class SalesOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    FULFILLED = "fulfilled"
    INVOICED = "invoiced"
    CANCELLED = "cancelled"


class SalesOrder(Base):
    __tablename__ = "erp_sales_orders"
    __table_args__ = (
        Index("ix_erp_so_number", "order_number", unique=True),
        Index("ix_erp_so_company", "company_id"),
        Index("ix_erp_so_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_quotes.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_companies.id"))
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_opportunities.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id"))
    status: Mapped[SalesOrderStatus] = mapped_column(Enum(SalesOrderStatus), default=SalesOrderStatus.DRAFT)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalesOrderLine(Base):
    __tablename__ = "erp_sales_order_lines"
    __table_args__ = (Index("ix_erp_so_lines_order", "order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_sales_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)


# ── Goods Receipt Notes (GRN) ───────────────────────────────────────

class GrnStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class GoodsReceipt(Base):
    __tablename__ = "erp_goods_receipts"
    __table_args__ = (
        Index("ix_erp_grn_po", "po_id"),
        Index("ix_erp_grn_number", "grn_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grn_number: Mapped[str] = mapped_column(String(50), nullable=False)
    po_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_purchase_orders.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_warehouses.id"))
    received_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[GrnStatus] = mapped_column(Enum(GrnStatus), default=GrnStatus.DRAFT)
    received_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GrnLine(Base):
    __tablename__ = "erp_grn_lines"
    __table_args__ = (Index("ix_erp_grn_lines_grn", "grn_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grn_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_goods_receipts.id", ondelete="CASCADE"), nullable=False)
    po_line_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_purchase_order_lines.id"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity_received: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


# ── RFQs / Supplier Quotes ──────────────────────────────────────────

class RfqStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    CLOSED = "closed"
    AWARDED = "awarded"
    CANCELLED = "cancelled"


class Rfq(Base):
    __tablename__ = "erp_rfqs"
    __table_args__ = (
        Index("ix_erp_rfqs_number", "rfq_number", unique=True),
        Index("ix_erp_rfqs_req", "requisition_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_number: Mapped[str] = mapped_column(String(50), nullable=False)
    requisition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_requisitions.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    status: Mapped[RfqStatus] = mapped_column(Enum(RfqStatus), default=RfqStatus.DRAFT)
    issued_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    awarded_quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    awarded_po_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_purchase_orders.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RfqLine(Base):
    __tablename__ = "erp_rfq_lines"
    __table_args__ = (Index("ix_erp_rfq_lines_rfq", "rfq_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_rfqs.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    target_price: Mapped[float | None] = mapped_column(Float)


class RfqVendor(Base):
    __tablename__ = "erp_rfq_vendors"
    __table_args__ = (Index("ix_erp_rfq_vendors_rfq", "rfq_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_rfqs.id", ondelete="CASCADE"), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_vendors.id"), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupplierQuoteStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"


class SupplierQuote(Base):
    __tablename__ = "erp_supplier_quotes"
    __table_args__ = (
        Index("ix_erp_sq_rfq", "rfq_id"),
        Index("ix_erp_sq_vendor", "vendor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_rfqs.id", ondelete="CASCADE"), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_vendors.id"), nullable=False)
    status: Mapped[SupplierQuoteStatus] = mapped_column(Enum(SupplierQuoteStatus), default=SupplierQuoteStatus.SUBMITTED)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    terms: Mapped[str | None] = mapped_column(Text)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupplierQuoteLine(Base):
    __tablename__ = "erp_supplier_quote_lines"
    __table_args__ = (Index("ix_erp_sql_quote", "supplier_quote_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_supplier_quotes.id", ondelete="CASCADE"), nullable=False)
    rfq_line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_rfq_lines.id"), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


# ── Shipments (#75) ─────────────────────────────────────────────────

class CarrierType(str, enum.Enum):
    FEDEX = "fedex"
    UPS = "ups"
    DHL = "dhl"
    USPS = "usps"
    DPD = "dpd"
    OTHER = "other"


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    LABEL_CREATED = "label_created"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    CANCELLED = "cancelled"


class Shipment(Base):
    """A shipment ties a tracking number from a carrier to a Sales Order or Invoice."""

    __tablename__ = "erp_shipments"
    __table_args__ = (
        Index("ix_erp_shipments_so", "sales_order_id"),
        Index("ix_erp_shipments_invoice", "invoice_id"),
        Index("ix_erp_shipments_carrier_tn", "carrier", "tracking_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_sales_orders.id"))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_invoices.id"))
    carrier: Mapped[CarrierType] = mapped_column(Enum(CarrierType), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False)
    shipped_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    label_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Batches / Lots (for products with track_batch=true) ─────────────

class StockBatch(Base):
    __tablename__ = "erp_stock_batches"
    __table_args__ = (
        Index("ix_erp_batches_product", "product_id"),
        Index("ix_erp_batches_expiry", "expiry_date"),
        Index("ix_erp_batches_code", "product_id", "batch_code", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_warehouses.id"))
    batch_code: Mapped[str] = mapped_column(String(100), nullable=False)
    mfg_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qty_received: Mapped[float] = mapped_column(Float, default=0.0)
    qty_on_hand: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_unit: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Serial numbers (for products with track_serial=true) ────────────

class SerialStatus(str, enum.Enum):
    IN_STOCK = "in_stock"
    SOLD = "sold"
    IN_TRANSIT = "in_transit"
    SCRAPPED = "scrapped"
    RETURNED = "returned"


class StockSerial(Base):
    __tablename__ = "erp_stock_serials"
    __table_args__ = (
        Index("ix_erp_serials_product", "product_id"),
        Index("ix_erp_serials_status", "status"),
        Index("ix_erp_serials_no", "product_id", "serial_no", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(120), nullable=False)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_stock_batches.id"))
    current_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("erp_warehouses.id"))
    status: Mapped[SerialStatus] = mapped_column(Enum(SerialStatus), default=SerialStatus.IN_STOCK)
    received_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
