"""Minimal additive migration helper — runs idempotent ALTER TABLE statements
on startup. We're not using Alembic (yet); this lives alongside Base.metadata.create_all
to cover columns added to existing tables.

Each statement uses `ADD COLUMN IF NOT EXISTS` (Postgres 9.6+) so re-running is safe.
"""

import logging

from sqlalchemy import text

from app.database import engine

logger = logging.getLogger(__name__)


# ── Additive migrations ───────────────────────────────────────────────
# Format: "<description>": "SQL statement"
MIGRATIONS: dict[str, str] = {
    "dms_documents.expiry_date":
        "ALTER TABLE dms_documents ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMPTZ",
    "erp_products.track_batch":
        "ALTER TABLE erp_products ADD COLUMN IF NOT EXISTS track_batch BOOLEAN NOT NULL DEFAULT false",
    "erp_products.track_serial":
        "ALTER TABLE erp_products ADD COLUMN IF NOT EXISTS track_serial BOOLEAN NOT NULL DEFAULT false",
    "erp_stock_movements.batch_id":
        "ALTER TABLE erp_stock_movements ADD COLUMN IF NOT EXISTS batch_id UUID",
    "erp_stock_movements.serial_id":
        "ALTER TABLE erp_stock_movements ADD COLUMN IF NOT EXISTS serial_id UUID",
    "users.timezone":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) NOT NULL DEFAULT 'UTC'",
    "users.language":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) NOT NULL DEFAULT 'en'",
    "erp_bank_transactions.matched_journal_entry_id":
        "ALTER TABLE erp_bank_transactions ADD COLUMN IF NOT EXISTS matched_journal_entry_id UUID",
    "erp_bank_transactions.notes":
        "ALTER TABLE erp_bank_transactions ADD COLUMN IF NOT EXISTS notes TEXT",
    "erp_journal_lines.cost_center_id":
        "ALTER TABLE erp_journal_lines ADD COLUMN IF NOT EXISTS cost_center_id UUID",
    "erp_journal_lines.profit_center_id":
        "ALTER TABLE erp_journal_lines ADD COLUMN IF NOT EXISTS profit_center_id UUID",
    "users.phone":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(40)",
    "users.notify_email":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_email BOOLEAN NOT NULL DEFAULT true",
    "users.notify_sms":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_sms BOOLEAN NOT NULL DEFAULT false",
    "users.totp_secret":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64)",
    "users.is_totp_enabled":
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_totp_enabled BOOLEAN NOT NULL DEFAULT false",
    "time_entries.timesheet_id":
        "ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS timesheet_id UUID",
    "erp_invoices.stripe_session_id":
        "ALTER TABLE erp_invoices ADD COLUMN IF NOT EXISTS stripe_session_id VARCHAR(120)",
    "erp_invoices.stripe_payment_intent_id":
        "ALTER TABLE erp_invoices ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(120)",
    "erp_invoices.company_id":
        "ALTER TABLE erp_invoices ADD COLUMN IF NOT EXISTS company_id UUID",
    "projects.workspace_id":
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "crm_companies.workspace_id":
        "ALTER TABLE crm_companies ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "erp_vendors.workspace_id":
        "ALTER TABLE erp_vendors ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "crm_contacts.workspace_id":
        "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "crm_leads.workspace_id":
        "ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "crm_opportunities.workspace_id":
        "ALTER TABLE crm_opportunities ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "crm_quotes.workspace_id":
        "ALTER TABLE crm_quotes ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "erp_invoices.workspace_id":
        "ALTER TABLE erp_invoices ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "erp_expenses.workspace_id":
        "ALTER TABLE erp_expenses ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "erp_purchase_orders.workspace_id":
        "ALTER TABLE erp_purchase_orders ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "erp_assets.workspace_id":
        "ALTER TABLE erp_assets ADD COLUMN IF NOT EXISTS workspace_id UUID",
    "dms_folders.workspace_id":
        "ALTER TABLE dms_folders ADD COLUMN IF NOT EXISTS workspace_id UUID",
    # Soft-delete (#7 / #22) — flagship tables gain deleted_at. Partial
    # indexes keep lookups on the active rows fast without bloating for
    # the vast majority that aren't trashed.
    "projects.deleted_at":
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "crm_companies.deleted_at":
        "ALTER TABLE crm_companies ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "erp_invoices.deleted_at":
        "ALTER TABLE erp_invoices ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "dms_documents.deleted_at":
        "ALTER TABLE dms_documents ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    "ix_projects_deleted":
        "CREATE INDEX IF NOT EXISTS ix_projects_deleted ON projects (deleted_at) WHERE deleted_at IS NOT NULL",
    "ix_crm_companies_deleted":
        "CREATE INDEX IF NOT EXISTS ix_crm_companies_deleted ON crm_companies (deleted_at) WHERE deleted_at IS NOT NULL",
    "ix_erp_invoices_deleted":
        "CREATE INDEX IF NOT EXISTS ix_erp_invoices_deleted ON erp_invoices (deleted_at) WHERE deleted_at IS NOT NULL",
    "ix_dms_documents_deleted":
        "CREATE INDEX IF NOT EXISTS ix_dms_documents_deleted ON dms_documents (deleted_at) WHERE deleted_at IS NOT NULL",

    # ── Performance indexes ───────────────────────────────────────────
    # Postgres does NOT auto-index foreign keys (only PKs / UNIQUEs). The
    # following close that gap on the highest-traffic FK columns plus a
    # handful of status / composite filters that show up on every list page.
    "ix_crm_companies_workspace":
        "CREATE INDEX IF NOT EXISTS ix_crm_companies_workspace ON crm_companies (workspace_id)",
    "ix_crm_quotes_company":
        "CREATE INDEX IF NOT EXISTS ix_crm_quotes_company ON crm_quotes (company_id)",
    "ix_crm_quotes_contact":
        "CREATE INDEX IF NOT EXISTS ix_crm_quotes_contact ON crm_quotes (contact_id)",
    "ix_crm_quotes_status":
        "CREATE INDEX IF NOT EXISTS ix_crm_quotes_status ON crm_quotes (status)",
    "ix_crm_leads_contact":
        "CREATE INDEX IF NOT EXISTS ix_crm_leads_contact ON crm_leads (contact_id)",
    "ix_crm_leads_assignee":
        "CREATE INDEX IF NOT EXISTS ix_crm_leads_assignee ON crm_leads (assigned_to_id)",
    "ix_crm_interactions_opportunity":
        "CREATE INDEX IF NOT EXISTS ix_crm_interactions_opportunity ON crm_interactions (opportunity_id)",
    "ix_crm_interactions_user":
        "CREATE INDEX IF NOT EXISTS ix_crm_interactions_user ON crm_interactions (user_id)",
    "ix_crm_contracts_opportunity":
        "CREATE INDEX IF NOT EXISTS ix_crm_contracts_opportunity ON crm_contracts (opportunity_id)",
    "ix_crm_contracts_status":
        "CREATE INDEX IF NOT EXISTS ix_crm_contracts_status ON crm_contracts (status)",
    "ix_crm_cm_contact":
        "CREATE INDEX IF NOT EXISTS ix_crm_cm_contact ON crm_campaign_members (contact_id)",
    "ix_crm_cm_lead":
        "CREATE INDEX IF NOT EXISTS ix_crm_cm_lead ON crm_campaign_members (lead_id)",
    "ix_crm_cm_status":
        "CREATE INDEX IF NOT EXISTS ix_crm_cm_status ON crm_campaign_members (status)",
    "ix_crm_emails_opportunity":
        "CREATE INDEX IF NOT EXISTS ix_crm_emails_opportunity ON crm_emails (opportunity_id)",
    "ix_crm_commission_rules_user":
        "CREATE INDEX IF NOT EXISTS ix_crm_commission_rules_user ON crm_commission_rules (user_id)",
    "ix_crm_commissions_opportunity":
        "CREATE INDEX IF NOT EXISTS ix_crm_commissions_opportunity ON crm_commissions (opportunity_id)",
    "ix_crm_commissions_rule":
        "CREATE INDEX IF NOT EXISTS ix_crm_commissions_rule ON crm_commissions (rule_id)",
    "ix_crm_territories_owner":
        "CREATE INDEX IF NOT EXISTS ix_crm_territories_owner ON crm_territories (owner_id)",
    "ix_crm_drip_enr_sequence":
        "CREATE INDEX IF NOT EXISTS ix_crm_drip_enr_sequence ON crm_drip_enrollments (sequence_id)",
    "ix_crm_drip_enr_contact":
        "CREATE INDEX IF NOT EXISTS ix_crm_drip_enr_contact ON crm_drip_enrollments (contact_id)",
    "ix_erp_invoices_vendor":
        "CREATE INDEX IF NOT EXISTS ix_erp_invoices_vendor ON erp_invoices (vendor_id)",
    "ix_erp_invoices_company":
        "CREATE INDEX IF NOT EXISTS ix_erp_invoices_company ON erp_invoices (company_id)",
    "ix_erp_expenses_user":
        "CREATE INDEX IF NOT EXISTS ix_erp_expenses_user ON erp_expenses (user_id)",
    "ix_erp_expenses_vendor":
        "CREATE INDEX IF NOT EXISTS ix_erp_expenses_vendor ON erp_expenses (vendor_id)",
    "ix_erp_assets_status":
        "CREATE INDEX IF NOT EXISTS ix_erp_assets_status ON erp_assets (status)",
    "ix_erp_budget_lines_account":
        "CREATE INDEX IF NOT EXISTS ix_erp_budget_lines_account ON erp_budget_lines (account_id)",
    "ix_erp_bank_account":
        "CREATE INDEX IF NOT EXISTS ix_erp_bank_account ON erp_bank_transactions (account_id)",
    "ix_erp_bank_matched_invoice":
        "CREATE INDEX IF NOT EXISTS ix_erp_bank_matched_invoice ON erp_bank_transactions (matched_invoice_id) WHERE matched_invoice_id IS NOT NULL",
    "ix_erp_bank_matched_expense":
        "CREATE INDEX IF NOT EXISTS ix_erp_bank_matched_expense ON erp_bank_transactions (matched_expense_id) WHERE matched_expense_id IS NOT NULL",
    "ix_erp_bank_matched_journal":
        "CREATE INDEX IF NOT EXISTS ix_erp_bank_matched_journal ON erp_bank_transactions (matched_journal_entry_id) WHERE matched_journal_entry_id IS NOT NULL",
    "ix_erp_stock_warehouse":
        "CREATE INDEX IF NOT EXISTS ix_erp_stock_warehouse ON erp_stock_movements (warehouse_id)",
    "ix_erp_so_lines_product":
        "CREATE INDEX IF NOT EXISTS ix_erp_so_lines_product ON erp_sales_order_lines (product_id) WHERE product_id IS NOT NULL",
    "ix_dms_fp_user":
        "CREATE INDEX IF NOT EXISTS ix_dms_fp_user ON dms_folder_permissions (user_id)",
    "ix_dms_retention_folder":
        "CREATE INDEX IF NOT EXISTS ix_dms_retention_folder ON dms_retention_policies (folder_id)",
    "ix_activity_user":
        "CREATE INDEX IF NOT EXISTS ix_activity_user ON activity_logs (user_id)",
    "ix_comments_user":
        "CREATE INDEX IF NOT EXISTS ix_comments_user ON comments (user_id)",
    # ── Composite hot-filter indexes ──────────────────────────────────
    "ix_erp_invoices_status_due":
        "CREATE INDEX IF NOT EXISTS ix_erp_invoices_status_due ON erp_invoices (status, due_date)",
    "ix_crm_quotes_company_status":
        "CREATE INDEX IF NOT EXISTS ix_crm_quotes_company_status ON crm_quotes (company_id, status) WHERE company_id IS NOT NULL",
    "ix_projects_ws_status":
        "CREATE INDEX IF NOT EXISTS ix_projects_ws_status ON projects (workspace_id, status) WHERE workspace_id IS NOT NULL",
    "ix_erp_vendors_ws_active":
        "CREATE INDEX IF NOT EXISTS ix_erp_vendors_ws_active ON erp_vendors (workspace_id, is_active) WHERE workspace_id IS NOT NULL",

    # ── Webhook retries + API key scopes (#8, #9) ─────────────────────
    "webhook_deliveries.attempts":
        "ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0",
    "webhook_deliveries.next_attempt_at":
        "ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ",
    "webhook_deliveries.delivered_at":
        "ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ",
    "ix_wd_pending":
        "CREATE INDEX IF NOT EXISTS ix_wd_pending ON webhook_deliveries (next_attempt_at) WHERE next_attempt_at IS NOT NULL",
    "api_keys.scopes":
        "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS scopes VARCHAR(2000) NOT NULL DEFAULT ''",

    # ── Phase 3 (business completeness) ───────────────────────────────
    # Workspace plan-limit overrides — NULL means "inherit from plan tier".
    "workspaces.max_users":
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS max_users INTEGER",
    "workspaces.max_projects":
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS max_projects INTEGER",
    "workspaces.max_storage_mb":
        "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS max_storage_mb INTEGER",

    # Vendor performance (#4) — PO receive-date + QC defect rate.
    "erp_purchase_orders.received_date":
        "ALTER TABLE erp_purchase_orders ADD COLUMN IF NOT EXISTS received_date TIMESTAMPTZ",
    "erp_purchase_orders.defect_rate":
        "ALTER TABLE erp_purchase_orders ADD COLUMN IF NOT EXISTS defect_rate DOUBLE PRECISION",

    # Inventory barcode + bin support (#5).
    "erp_products.barcode":
        "ALTER TABLE erp_products ADD COLUMN IF NOT EXISTS barcode VARCHAR(64)",
    "ix_erp_products_barcode":
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_erp_products_barcode ON erp_products (barcode) WHERE barcode IS NOT NULL",
    "erp_stock_movements.bin_id":
        "ALTER TABLE erp_stock_movements ADD COLUMN IF NOT EXISTS bin_id UUID",

    # Tier pricing fix — old unique index blocked multiple tiers per product.
    "drop_old_pli_unique":
        "DROP INDEX IF EXISTS ix_pli_list_product",
    "ix_pli_list_product_tier":
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_pli_list_product_tier "
        "ON pricing_list_items (price_list_id, product_id, min_quantity)",
}


_MIGRATION_LOCK_KEY = 73126903  # arbitrary but stable; serialises across replicas


async def run_additive_migrations() -> None:
    """Run each statement in its own transaction so one failure doesn't poison
    the rest (Postgres aborts the whole txn on any DDL error). Wrap the whole
    pass in a session-level advisory lock so the two backend replicas don't
    race each other on `CREATE INDEX IF NOT EXISTS` — concurrent index creation
    can hit `pg_class_relname_nsp_index` unique-violations even with the IF NOT
    EXISTS guard, because it races between the existence check and the insert."""

    async with engine.connect() as lock_conn:
        await lock_conn.execute(text("SELECT pg_advisory_lock(:k)").bindparams(k=_MIGRATION_LOCK_KEY))
        try:
            # Best-effort: enable pgvector. No-op if not installed in the image.
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception:
                logger.info("pgvector extension not available — semantic search disabled", exc_info=True)
            for label, sql in MIGRATIONS.items():
                try:
                    async with engine.begin() as conn:
                        await conn.execute(text(sql))
                except Exception:
                    logger.warning("Migration failed for %s", label, exc_info=True)
        finally:
            await lock_conn.execute(text("SELECT pg_advisory_unlock(:k)").bindparams(k=_MIGRATION_LOCK_KEY))
