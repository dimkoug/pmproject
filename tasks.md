# Tasks

## Active backlog

### Remaining feature work (from Tier-1 roadmap)

- [x] **#43 Timesheet submission & approval workflow** ✅ — new `timesheets` table grouping `time_entries` by `(user_id, week_start)` (Monday-anchored, unique constraint); `time_entries.timesheet_id` nullable FK (additive migration); submit → approver decision flow with `TimesheetStatus = draft|submitted|approved|rejected`; auto-pulls all the user's entries within the week into the sheet on create or submit (sums to `total_hours`); endpoints `/api/hr/timesheets/{me,inbox,{id}/submit,{id}/decide}`; permissions `hr.timesheet.submit` + `hr.timesheet.approve`; TimesheetsPage at `/admin/hr/timesheets` with My / Inbox tabs, "Open this week" button, lock indicator, inline submit / approve / reject with note modals.

- [x] **#45 2FA / TOTP for admin accounts** ✅ — `users.totp_secret` + `users.is_totp_enabled` columns (additive migrations); `pyotp` + `qrcode` added to requirements; `/api/auth/totp/{enroll,confirm,disable}` endpoints; `/auth/login` accepts optional `totp_code` and returns `detail: "TOTP_REQUIRED"` when enabled but missing; LoginPage transparently surfaces a 6-digit code field on the TOTP_REQUIRED challenge; SecurityPage at `/admin/security` runs the enrolment flow (start → show secret + provisioning URI → verify code → done) and a Disable form (password + current code). Sensitive-op gating on `admin.*` / `finance.journal.post` not yet wired — that's a follow-up.

- [x] **#46 Workspace isolation (multi-tenancy) — Phase-1 MVP** ✅ — `workspace_id` nullable FK on flagship tables Project + Company + Vendor (additive migrations); boot-time `seed_default_workspace_and_backfill()` ensures a "Default" workspace exists and back-fills existing NULL `workspace_id` rows; new `app/services/workspaces.py` with `get_active_workspace_id(request, user, db)` that resolves in order: `X-Workspace-Id` header (validated against `WorkspaceMember`; admin bypasses), user's first membership, fallback to Default. Applied to `GET/POST /api/projects`, `GET/POST /api/crm/companies`, `GET/POST /api/erp/vendors` — listings auto-filter (`workspace_id = ws OR workspace_id IS NULL` for legacy safety), creates auto-stamp. `GET /api/me/workspaces` returns the user's visible workspaces with `active: true` flag. Frontend: `apiSlice.prepareHeaders` injects `X-Workspace-Id` from `localStorage.activeWorkspaceId`; user menu gains a Workspace dropdown when ≥2 are visible; switching dispatches `apiSlice.util.resetApiState()` so every RTK Query cache refetches under the new scope. **Per-entity rollout to remaining tables (leads, opps, invoices, folders, …) is mechanical follow-up — the helper, header, switcher, and seed are all in place.**

- [x] **#48 SSO actual wiring (OIDC callback)** ✅ — new `app/routers/sso.py`. `GET /api/sso/start?provider_id=` discovers `authorization_endpoint` via `/.well-known/openid-configuration`, mints a signed (HMAC-SHA256, 10-min TTL) `state` token (no server-side storage), 302s to provider. `GET /api/sso/callback` verifies state, POSTs the code to the token endpoint with `client_secret_masked` (the only secret column we have without a migration), decodes the `id_token` body for `email` + `name`, looks up or creates a user (`hashed_password = "!SSO_ONLY!"` for SSO-only accounts), issues our JWT, redirects to `/login/sso-callback#token=…&user_id=…` (URL fragment so token never hits server logs). `GET /api/sso/active` (public) returns active providers; LoginPage renders SSO buttons + handles `?sso_error=` query string. New SsoCallbackPage consumes the fragment, calls `/api/auth/me`, dispatches `setCredentials`, navigates home. Removed the matching stubs from `cross.py`.

- [x] **#49 Semantic search + doc Q&A** ✅ — switched Postgres image to `pgvector/pgvector:pg16`; `CREATE EXTENSION vector` runs at startup. New `dms_document_chunks` table with `embedding Vector(1536)` (portable: JSON variant on sqlite for tests). `app/services/embeddings.py` calls OpenAI-compatible `/embeddings` API via `httpx` when `LLM_API_KEY` is set, else deterministic mock (token-frequency hashed vector) so the feature stays demoable without API credits. ~500-char overlap chunker. Endpoints `/api/dms/{embeddings/rebuild,search/semantic,qa}` use pgvector's `<=>` cosine distance for ranking; QA stitches top chunks → LLM if configured, else evidence-based fallback that quotes the top 3 passages. DocQaPage at `/documents/qa` with mode toggle (Ask / Search), live re-index button, source citations.

- [ ] **#51 Bank feed integration (Plaid / TrueLayer)**
  Plaid Link flow to connect a bank. Webhook receives transactions → writes to `erp_bank_transactions`. Auto-match runs via existing endpoint. Admin UI: connected banks + sync status.

- [x] **#52 AI project-plan generation from brief** ✅ — `app/services/llm.py` calls any OpenAI-compatible chat-completions API via `httpx` (no SDK dependency); env vars `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` / `LLM_TIMEOUT_SECONDS`. When `LLM_API_KEY` is unset, falls back to a deterministic heuristic mock (detects software/construction/marketing keywords) so the feature stays demoable. Celery task `generate_project_plan_task` runs on the `reports` queue. Endpoints: `POST /api/projects/{id}/ai-plan/start` enqueues + returns `task_id` (polled via existing `/api/celery-tasks/{id}`); `POST /api/projects/{id}/ai-plan/commit` takes the (optionally edited) plan and creates Tasks (`duration_days = estimate_hours/8`), Risks (impact/likelihood from low/med/high strings), Deliverables, and Milestones (zero-duration tasks prefixed with 🎯). Permission reuses `projects.task.create`. Frontend `AiPlanModal` mounted in TasksPage with a new "⚡ AI plan" button — submit brief → poll task → review-and-edit screen with per-row remove → Accept & create.

---

### New ERP features — Tier 1 (proposed, grouped by bundle)

Each bundle is coherent and deliverable as one effort. Pick bundles rather than individual items.

#### Bundle A — "Procurement completion" (close the P2P loop) ✅ shipped

- [x] **#64 Sales Orders (Quote → SO → Invoice)** — `erp_sales_orders` + `erp_sales_order_lines`; `POST /erp/sales-orders`, `POST /erp/sales-orders/from-quote/{quote_id}`, `PATCH /erp/sales-orders/{id}/status`, `POST /erp/sales-orders/{id}/invoice`; status workflow `draft → confirmed → fulfilled → invoiced`; SalesOrdersPage with convert-from-quote + per-row status/invoice actions; nav under Sales → Pipeline; permissions `sales.order.view` / `sales.order.manage`.

- [x] **#65 Goods Receipt Notes (GRN)** — `erp_goods_receipts` + `erp_grn_lines` + new `erp_purchase_order_lines` (PO lines were missing); `POST /erp/goods-receipts` validates received ≤ outstanding; `POST /erp/goods-receipts/{id}/confirm` posts inbound `StockMovement`s, bumps `po_line.quantity_received`, flips PO to `received` when fully received; GoodsReceiptsPage + per-row Confirm; nav under Finance → Payables; permission `finance.grn.manage`.

- [x] **#66 RFQ / Supplier quotes** — `erp_rfqs` + `erp_rfq_lines` + `erp_rfq_vendors` + `erp_supplier_quotes` + `erp_supplier_quote_lines`; `POST /erp/rfqs`, `POST /erp/rfqs/{id}/send`, `POST /erp/rfqs/{id}/quotes` (submit supplier quote), `GET /erp/rfqs/{id}/quotes` (compare), `POST /erp/rfqs/{id}/award` (creates PO from winner, marks losers); RfqsPage with inline compare card; nav under Finance → Payables; permission `finance.rfq.manage`.

#### Bundle B — "Inventory depth" (regulated-product ready) ✅ shipped

- [x] **#67 Batch/Lot + Serial + Expiry tracking** — `Product.track_batch` / `Product.track_serial` flags (additive migrations); `StockMovement.batch_id` / `serial_id` nullable FKs; new `erp_stock_batches` (batch_code, expiry_date, mfg_date, qty_received, qty_on_hand, cost_per_unit) + `erp_stock_serials` (serial_no, status enum: in_stock/sold/in_transit/scrapped/returned); `GET /erp/batches` with `expiring_within_days` filter and dedicated `GET /erp/batches/expiring-soon`; `POST /erp/batches` auto-writes an inbound StockMovement; `/erp/batches/{id}/adjust` for qty deltas; `/erp/serials` CRUD with status transitions that write stock movements; BatchesPage + SerialsPage under Finance → Operations; permissions `inventory.batch.manage` / `inventory.serial.manage`.

- [x] **#68 Cross-cutting tags** — `tags` table + polymorphic `tag_links(tag_id, entity_type, entity_id)` with unique constraint; full CRUD at `/api/tags`; `GET /api/tags/for?entity_type=&entity_id=`, `POST /api/tags/{id}/attach`, `DELETE /api/tags/{id}/detach`; TagChip + TagPicker shell components (inline combobox with search + colored chips); Admin → Taxonomy → Tags catalog page; TagPicker auto-mounted in every DetailDrawer header so any entity type gets tags without per-body integration; permission `admin.tag.manage`.

#### Bundle C — "International readiness" ✅ shipped

- [x] **#69 i18n scaffolding** — `react-i18next` + `i18next` installed; `src/i18n/index.ts` initializes with `en` locale; `src/i18n/en.json` seeded with common/shell/apps/nav namespaces; `src/i18n/format.ts` exports `useFormat()` (formatDate/formatDateTime/formatTime/formatRelative/formatCurrency/formatNumber/formatPercent) with cached `Intl.*` formatters; SuiteBar wired to `useTranslation()`; language `<select>` in user menu writes through `/api/auth/me/settings` and calls `i18n.changeLanguage()`; structure ready for additional locales (add to `SUPPORTED_LANGUAGES` + resources).

- [x] **#70 User timezone + date localization** — `users.timezone` + `users.language` columns (additive migrations with `default 'UTC'` / `'en'`); `UserRead` schema exposes both; `PATCH /api/auth/me/settings` validates timezone via `zoneinfo.ZoneInfo` before saving; frontend `authSlice` stores fields + new `patchUser` action; `useFormat()` hook resolves user.timezone as `Intl.DateTimeFormat.timeZone`; IANA zone `<select>` in user menu (23 common zones); drawer tabs (Comments, Activity) and drawer body registrations (Invoice/Opportunity/Company/Lead/Expense/Asset Overviews) use the hook instead of `toLocaleString()` / `$${x.toLocaleString()}`; notification timestamps localized.

#### Bundle D — "Operations productivity" ✅ shipped

- [x] **#71 Bank reconciliation workbench** — `BankTransaction.matched_journal_entry_id` + `notes` (additive migrations); rebuilt `POST /erp/bank-transactions/{id}/match` to take a JSON body supporting invoice / expense / journal targets; new `DELETE /erp/bank-transactions/{id}/match` (unmatch); new `POST /erp/bank-transactions/{id}/create-journal` (one-shot: posts a balanced JE + links the bank txn to it); BankReconciliationPage at `/finance/reconciliation` — two-pane workbench with bank txns on the left, ranked candidates (invoice / expense / journal, sorted by amount delta, close-match highlighted) on the right; per-row Match / Unmatch / "Create journal entry" actions; show-matched toggle; nav under Finance → Ledger.

- [x] **#72 Automation rules (IFTTT-style)** — `automation_rules` (trigger_event, JSONB conditions, JSONB actions, is_active) + `automation_rule_runs` (audit log of evaluations); `app/services/automation.py` with `fire_event(db, event, payload)` evaluator, condition matchers (`==`, `!=`, `>`, `>=`, `<`, `<=`, `contains`, `in`, `exists`) on dotted-path payload fields; action runners for `notify_user` / `add_tag` / `post_webhook` / `log` (with `{placeholder}` interpolation); evaluator hooked into `log_audit()` so every audited mutation auto-fires matching rules; `/api/automation/{catalog,rules,runs}` endpoints; AutomationPage at `/admin/automation` — DataTable of rules + recent-runs panel + modal RuleEditor with trigger dropdown, condition rows, and per-action-type parameter forms; permission `admin.automation.manage`.

#### Bundle E — "HR foundation" ✅ shipped

- [x] **#73 HR — employees + leave + attendance** — new `app/models/hr.py` with `Employee` (optionally linked to `users`, plus number / department / job_title / hire_date / manager_id / termination_date), `LeaveRequest` (type enum: vacation/sick/personal/bereavement/maternity/paternity/unpaid/other; status enum: pending/approved/rejected/cancelled; auto-computed days), `Attendance` (work_date / check_in / check_out / hours_worked / source enum: web/mobile/kiosk/import/manual); router `/api/hr/{employees,leave-requests,attendance,dashboard}` with self-service `/employees/me`, `/attendance/check-in`, `/attendance/check-out` (idempotent — returns the open record if already checked in); 7 new permissions (`hr.employee.view/manage`, `hr.leave.view/request/approve`, `hr.attendance.view/manage`); Admin sub-app at `/admin/hr` with **Overview** (stat cards: active employees, pending leave, on leave today, today's check-ins, hours logged 7d + per-user check-in/out widget), **Employees**, **Leave** (approve/reject inline), **Attendance** (self check-in + manual record entry); employee drawer body registered for row-click peek.

---

### New ERP features — Tier 2 (larger efforts, single-bundle each)

- [x] **#74 Customer portal** ✅ — new `portal_tokens` table for single-use magic links; new `app/routers/portal.py` with admin side (`POST /api/admin/portal/magic-link` requires `sales.company.manage`, returns the URL to share + expiry) and customer side (`POST /api/portal/exchange` swaps a token for a 60-min portal-scoped JWT with `kind="portal"` claim, then `GET /api/portal/{me,invoices}` and `POST /api/portal/invoices/{id}/checkout` for Stripe payment). `Invoice.company_id` added (additive migration) so invoices can be scoped to a customer. Customer-facing routes outside SuiteShell at `/portal/login` (token exchange) and `/portal` (invoice list with Pay-now buttons). CompaniesPage gets a "Portal link" action that copies the magic URL to clipboard.

- [x] **#75 Shipping provider integration** ✅ — new `erp_shipments` table with `(carrier, tracking_number)` unique index, optional FK to either Sales Order or Invoice, status enum (`pending/label_created/in_transit/delivered/exception/cancelled`), shipped/delivered/expected dates. `CarrierAdapter` interface in `app/routers/shipping.py` with stub manual adapter (real FedEx/UPS/DHL wiring is the extension point). Endpoints: `/api/shipping/{carriers,shipments,shipments/{id}/status}`. Public webhook `POST /api/webhooks/shipping` accepts `{carrier, tracking_number, status}` from any aggregator (Shippo / EasyPost / AfterShip) — looks up the shipment and applies the status. Permission `sales.shipment.manage`. ShipmentsPage at `/finance/shipments` (Operations group) with attach-to-SO/invoice modal + status-update flow.

- [x] **#76 GDPR tooling** ✅ — new router `/api/gdpr/{export,me}`. `GET /api/gdpr/export` walks 10 tables (notifications, comments, activity_log, time_entries, team_members, audit_entries, user_permissions, project_members, hr_employees, approvals, hr_leave_requests via employee link), bundles each into a JSON file, returns a ZIP with `_index.json` summary. `DELETE /api/gdpr/me?confirm=true` soft-deletes: anonymizes `email → redacted-{id}@deleted.local`, sets `name = "Deleted user"`, `is_active=false`, `hashed_password = "!DELETED!"` (referential integrity in audit log preserved). User menu gets "Download my data" + "Delete my account…" buttons (browser confirm + auto-logout).

- [x] **#77 Field-level permissions** ✅ — new `acl_field_masks` table (`unmask_codename` + `entity_type` + `fields[]`); `app/acl/resolver.py` gains `get_field_mask(db, user, entity_type, request)` (per-request cached) and `apply_field_mask(row, masked)` helpers; admin always bypasses; new permissions `admin.field_mask.manage` (admin CRUD) and `acl.unmask.finance_sensitive` (Finance group gets it by default); seeded 4 default masks (company.annual_revenue, lead.estimated_value, contact.{phone,email}, employee.{phone,email}); applied at `GET /api/crm/companies` and `GET /api/hr/employees`; `GET /api/me/field-masks` returns `{ entity_type: [hidden_field, ...] }` for the current user; admin CRUD at `/api/admin/acl/field-masks`; SecurityPage at `/admin/security` shows the user's hidden-field map.

- [x] **#78 Cost centers / profit centers** ✅ — `erp_cost_centers` + `erp_profit_centers` tables (code unique + name + description + is_active); `JournalLine.cost_center_id` / `profit_center_id` nullable FKs (additive migrations); CRUD endpoints `/erp/{cost,profit}-centers` (deactivate via DELETE — preserves history); journal-line write endpoint accepts the new optional fields; new report endpoint `/erp/reports/center-pnl?by={cost|profit}` aggregates revenue / expense / net per center across posted journal lines (including an "Unassigned" bucket); CentersPage at `/finance/centers` with cost/profit tabs, CRUD, and the per-center P&L table. Permission reuses `finance.account.manage` for CRUD and `finance.reports.view` for the report.

- [x] **#79 SMS notifications (Twilio)** ✅ — `app/services/sms.py` (Twilio REST adapter via `urllib.request` — no SDK dependency), `send_sms_now()` + `send_sms_task` Celery wrapper + `queue_sms()` helper that no-ops when `SMS_ENABLED=false`; new env vars `SMS_ENABLED` / `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM`; `users.phone` + `users.notify_email` + `users.notify_sms` columns (additive migrations + defaults); `UserRead` schema exposes them; `PATCH /api/auth/me/settings` accepts `phone` / `notify_email` / `notify_sms`; user menu Notifications section with email/SMS checkboxes + phone field. Existing notification call sites can now opt in: `if user.notify_sms and user.phone: queue_sms(user.phone, body)`.

- [x] **#80 Payment gateway (Stripe)** ✅ — `app/services/stripe_client.py` calls Stripe REST directly via `httpx` (no SDK dependency). New env vars `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY_DEFAULT`. `Invoice.stripe_session_id` + `Invoice.stripe_payment_intent_id` columns (additive migrations). `POST /api/erp/invoices/{id}/checkout-session` (gated by `finance.payment.record`) creates a one-line Checkout Session for the outstanding amount and returns the Stripe-hosted URL. `POST /api/webhooks/stripe` verifies the `Stripe-Signature` header (HMAC-SHA256 with 5-min replay window using stdlib only), handles `checkout.session.completed` (writes a `Payment` row, increments `paid_amount`, flips status to `paid` when fully paid) and `checkout.session.expired` (clears the abandoned session). InvoicesPage gets a per-row "Pay with Stripe" button (only on receivables that aren't yet paid) that opens the hosted checkout in a new tab.

---

### Long-term tracks (Tier 3 — not yet scoped as individual tasks)

Each of these is multi-week. Scope and break down before starting.

- **Manufacturing / MRP**: BOM, work orders, routing, work centers, shop floor, quality checks, scrap/waste, maintenance, cost calc (standard/actual). The biggest missing module.
- **Payroll**: payslips, tax deductions, statutory filings per jurisdiction. Depends on #73 HR foundation.
- **POS (Point of Sale)**: touchscreen register UI, cash drawer integration, offline mode, daily Z-report.
- **E-commerce connectors**: Shopify / WooCommerce / Amazon / eBay sync (orders down, stock up).
- **AI forecasting**: demand forecasting (stock), sales forecasting beyond the existing per-opportunity method.
- **Recruitment / ATS**: job postings, candidate pipeline, interview scheduling. Depends on #73.
- **Data warehouse integration + BI export**: CDC stream to Snowflake/BigQuery, Power BI / Tableau connector.
- **Mobile native apps** (iOS / Android): the web app is responsive but no native wrappers or offline-first caching.
- **Visual workflow builder** (drag & drop beyond the #72 rule-builder dropdown UI).

---

### Infrastructure (pending)

- [x] **#10 Put frontend assets behind a CDN** ✅ — nginx now sets `Cache-Control: public, max-age=31536000, immutable` on `/assets/*` (Vite's hashed-filename outputs are safe to long-cache forever) and `Cache-Control: no-cache` on the SPA shell at `/`. Reload-tested via `curl -sSI`. The CDN deployment path is now zero-config: point CloudFront / Cloudflare / Fastly at the nginx origin and the immutable header makes everything cache correctly without per-asset purging.

---

## Completed (ref)

### Shell + layout
- [x] #1 Build SuiteShell and top app bar
- [x] #2 Build AppLayout with contextual sidebar
- [x] #3 Promote CRM/ERP/DMS/Admin to top-level apps
- [x] #4 Relocate Projects under SuiteShell + clean project sidebar
- [x] #5 Add shell CSS and verify visual polish
- [x] #12 Extract reusable CommandBar and PageHeader components

### Scaling (Track A)
- [x] #6 Scale backend horizontally via docker compose replicas
- [x] #7 Widen PgBouncer pool and raise Postgres `max_connections`
- [x] #8 Split Redis into three dedicated instances (cache / broker / ws)
- [x] #9 Scale Celery workers and add a reports queue
- [x] #11 Add a Postgres read replica for reports and dashboards

### Page-per-route split (Track B)
- [x] #13 Split CrmPage into 16 per-route pages
- [x] #14 Split DmsPage into 8 per-route pages
- [x] #15 Split ErpPage into 21 per-route pages
- [x] #16 Remove catch-all `:tab` routes and delete monolithic pages

### ACL (Track C)
- [x] #17 Design and implement Permission/Group models + association tables
- [x] #18 Seed permission catalog and default groups
- [x] #19 Build permission resolver and FastAPI dependency
- [x] #20 Enforce permissions across all routers (partial — top writes covered)
- [x] #21 Add project-scoped ACL (project membership + per-project role)
- [x] #22 Build ACL management UI under Admin app (Groups / Permissions / Users / Inspector)

### DMS backend (Track D)
- [x] #23 Enforce `FolderPermission` in list/read endpoints
- [x] #24 DMS audit log: upload, download, view, delete, share
- [x] #25 Restore older version as current
- [x] #26 Advanced search filters (date / author / status / type)
- [x] #27 Document expiry date + Celery reminder task
- [x] #28 Retention auto-run via Celery Beat
- [x] #29 Image OCR via Tesseract (feature-flagged)
- [x] #30 Shareable public links with token + expiry
- [x] #31 Pluggable storage backend (local + S3-compatible)
- [x] #32 DMS reporting: usage, compliance, pending approvals

### DMS UI (Track E)
- [x] #33 Expiry-date input + expiring-soon widget
- [x] #34 Restore version button in version history
- [x] #35 Share dialog (create / list / revoke links)
- [x] #36 Advanced search filter panel
- [x] #37 DMS reports pages: Usage + Pending approvals
- [x] #38 Folder permissions editor

### Tests + seeding
- [x] #39 Add tests for new functionality (`test_acl.py` + `test_dms_new.py` + conftest fix; 60 tests passing)
- [x] #40 Seed all fake data into live stack (3 small + 3 large projects + 28 enterprise companies + 25 ERP vendors + DMS content + ERP ledger + admin cross-cutting — 77 populated tables)
- [x] #81 Tests for recent features — **41 new tests, all passing**. `test_pure_recent.py` (29): Stripe webhook signature + replay-window, SSO state token tamper detection, automation evaluator + dotted-path resolver + 8 op variants, embedding chunker overlap + empty-input, mock-embed determinism + cosine ordering, AI plan mock shape + keyword branching (software vs construction), field-mask helper. `test_workspaces.py` (6): default seed, header / membership / default-fallback resolution, admin bypass, company create stamps active workspace, list filters by workspace. `test_hr_tags.py` (6): tag create / attach / dedupe / detach roundtrip, timesheet Monday-anchoring, idempotent per-week, empty-submit rejection, auto-attach on submit, approve flow. Required portable column types: `JSONB → JSON.with_variant(JSONB, "postgresql")` on `automation_rules.{conditions,actions}`, `automation_rule_runs.payload`, and `dms_document_chunks.embedding`; `ARRAY(String) → JSON.with_variant(ARRAY, "postgresql")` on `acl_field_masks.fields` — sqlite-friendly so the test conftest's `create_all` succeeds, Postgres still gets the optimal types in production.

- [x] #82 DB performance pass — indexes, N+1 fixes, migration-runner hardening.
  - **40 new indexes** added via additive migrations (idempotent `CREATE INDEX IF NOT EXISTS`):
    - 32 missing FK columns (Postgres doesn't auto-index FKs — only PKs/UNIQUEs): `crm_companies.workspace_id`, `crm_quotes.{company_id,contact_id}`, `crm_leads.{contact_id,assigned_to_id}`, `crm_interactions.{opportunity_id,user_id}`, `crm_contracts.opportunity_id`, `crm_campaign_members.{contact_id,lead_id}`, `crm_emails.opportunity_id`, `crm_commission_rules.user_id`, `crm_commissions.{opportunity_id,rule_id}`, `crm_territories.owner_id`, `crm_drip_enrollments.{sequence_id,contact_id}`, `erp_invoices.{vendor_id,company_id}`, `erp_expenses.{user_id,vendor_id}`, `erp_budget_lines.account_id`, `erp_bank_transactions.{account_id,matched_invoice_id,matched_expense_id,matched_journal_entry_id}` (last 3 partial — `WHERE col IS NOT NULL`), `erp_stock_movements.warehouse_id`, `erp_sales_order_lines.product_id` (partial), `dms_folder_permissions.user_id`, `dms_retention_policies.folder_id`, `activity_logs.user_id`, `comments.user_id`.
    - 4 status / activity filters: `crm_quotes.status`, `crm_contracts.status`, `crm_campaign_members.status`, `erp_assets.status`.
    - 4 composite hot-filter indexes: `(status, due_date)` on `erp_invoices`, `(company_id, status)` on `crm_quotes`, `(workspace_id, status)` on `projects`, `(workspace_id, is_active)` on `erp_vendors`.
  - **3 N+1 patterns fixed**:
    - `GET /api/erp/rfqs/{id}/quotes` (`list_supplier_quotes`) — was 1 + N queries (one per supplier quote for its lines); now 1 + 1 batched `IN` query, grouped in Python. Biggest win on RFQ compare grids with 5+ vendors.
    - `GET /api/dms/entity-links` — was 1 + N (one `db.get(Document)` per link); now 1 + 1 batched `IN`, dict by id.
    - `GET /api/timeline/company/{id}` (linked-documents section) — same fix as above.
  - **Migration runner hardened** (`app/services/migrations.py`): each statement now runs in its own transaction (was sharing one — a single failure poisoned every subsequent statement with `current transaction is aborted`). Wrapped the full pass in `pg_advisory_lock(73126903)` so the two backend replicas don't race each other on `CREATE INDEX IF NOT EXISTS` (the existence-check / catalog-insert window can still hit `pg_class_relname_nsp_index` unique-violations under concurrent DDL).
  - **Test fix**: `test_list_permissions` was asserting `len(perms) == 58` against a catalog that's grown to ~80 entries with new features. Replaced with `len(perms) == len(CATALOG)` — anchored to the live catalog so adding permissions doesn't break the test.

### Collaboration + ops (Tier-1 done)
- [x] #41 Email delivery (SMTP) + Celery queue (password reset, signature requests, approval assignees, expiry reminders, @mention notifications)
- [x] #42 @mentions + notifications drawer (parser + resolve to user_id + Notification rows; SuiteBar popover with unread badge, mark-one/all-read, link navigation)
- [x] #44 Prometheus `/metrics` endpoint + Grafana (provisioned datasource + backend dashboard at `:3001`)
- [x] #47 CSV export everywhere (17 domains via `/api/export/{domain}.csv` + `downloadCsv` helper; Export buttons on Invoices / Expenses / Vendors / Companies / Leads / Opportunities)
- [x] #50 Real-time presence indicators (Redis-backed `/api/presence/*`, `usePresence` hook, `PresenceStack` avatar component — works across replicas)

### Enterprise-grade frontend refactor (Track F)
- [x] #53 Adopt Lucide icons + icon registry (`src/shell/icons.ts` — 70 curated icons, standardized stroke/size, replaced all inline SVGs + emoji glyphs)
- [x] #54 Typography + density scale + color restraint (CSS tokens `--fs-*`, `--density-*`; active nav items use neutral bg + accent border only)
- [x] #55 Density toggle in user menu (Comfortable / Compact, persists to `localStorage`, drives `html[data-density]`)
- [x] #56 Replace `prompt()` / `alert()` with FormModal (`FormModal.tsx` + `modalService.tsx` — `promptForValues` / `confirmAction` / `notifyUser`; 143 native calls across 38 files replaced)
- [x] #57 Build reusable DataTable (TanStack) (`src/shell/DataTable.tsx` — sort / filter / global search / sticky header / pagination / selection / density / skeletons / empty state / dark-mode)
- [x] #58 Apply DataTable to ~35 list pages (Finance, Sales, DMS, Admin list pages all migrated)
- [x] #59 Build DetailDrawer (side peek) (`src/shell/DetailDrawer.tsx` — right slide-in, URL-synced `?peek=ENTITY:ID`, ESC / click-outside, reusable `CommentsTab` / `ActivityTab` / `OverviewGrid`)
- [x] #60 Wire DetailDrawer into every list page (`onRowClick` peek on all list pages; 8 entity `DrawerBody` registrations: invoice, opportunity, company, lead, contact, vendor, expense, asset)
- [x] #61 Skeleton loading + rich empty states (`src/shell/Skeleton.tsx`, `src/shell/EmptyState.tsx`; DataTable renders them automatically)
- [x] #62 Global keyboard shortcuts (`useHotkeys` hook — Ctrl+K / `/` focus search, `?` cheatsheet, `n` auto-maps to primary CommandBar action; cheatsheet modal)
- [x] #63 Visual QA + dark-mode audit (verified all Lucide icons inherit `currentColor`, no stray hardcoded whites, `:focus-within` ring on DataTable search, dark-mode parity across new components)
