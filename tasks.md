# Tasks

## Active backlog

### Track F — Enterprise-grade frontend refactor (next up)

Queue order: 53 → 54 → 55 → 57 → 59 → 56 → 61 → 62 → 58 → 60 → 63.

- [ ] **#53 Adopt Lucide icons + icon registry**
  Install `lucide-react`. Create `src/shell/icons.ts` exporting a curated set. Replace every inline SVG and emoji glyph (`📁`, `☰`, hand-drawn SVGs in SuiteBar / AppSwitcher / app-nav / pages) with Lucide components. Consistent stroke width, 16/20 sizes. *Blocks #56, #59, #61.*

- [ ] **#54 Typography + density scale + color restraint**
  Tighten type scale: 0.82rem body, 0.95rem table rows, 1.1rem section headers, 1.35rem page titles. Add `--density` var (comfortable | compact). Reduce per-app accents to icon-tint only — sidebar stays neutral gray, only app-badge icon + active-nav-item border take the accent. Remove loud fills from stat cards. *Blocks #55, #57.*

- [ ] **#55 Density toggle in user menu** — blocked by #54
  "Compact rows / Comfortable rows" toggle in the SuiteBar user menu. Persist to `localStorage`. Sets `data-density` on `<html>` which drives the `--density` CSS var. Covers table row height, card padding, stat-card padding, form-group spacing.

- [ ] **#56 Replace `prompt()` / `alert()` with proper modals** — blocked by #53
  Build reusable `<FormModal>` (title, fields, cancel/primary, ESC, focus trap). Replace every `prompt()`/`alert()` across DMS / Sales / Finance (~40 sites): signatures, templates, retention, workflows, annotations, scans, leads, opps, quotes, campaigns, contracts, commissions, territories, drips, vendors, invoices, expenses, POs, assets, journal, bank, inventory, requisitions, credit-notes, depreciation, budgets, recurring.

- [ ] **#57 Build reusable DataTable (TanStack)** — blocked by #54
  Install `@tanstack/react-table`. Create `src/shell/DataTable.tsx` — column config + data prop + sort (click header), column filter, global search, sticky header, pagination footer (page size 25/50/100), row selection, density-aware rows, empty-state slot, skeleton rows. Dark-mode styled. Component only, no page wiring yet. *Blocks #58.*

- [ ] **#58 Apply DataTable to ~35 list pages** — blocked by #57
  Replace raw `<table>` markup everywhere. Finance (Invoices, Expenses, Vendors, POs, Assets, Accounts, Requisitions, Journal, Bank, Inventory, Budgets, CreditNotes, Recurring, Aging, Depreciation); Sales (Companies, Contacts, Leads, Interactions, Quotes, Campaigns, Contracts, Territories, Commissions, Emails, FollowUps, Drips, Health); DMS (Locks, Scans, Signatures, Templates, Retention); Admin (ACL Users, Permissions catalog, Activity log). *Blocks #60, #63.*

- [ ] **#59 Build DetailDrawer (side peek)** — blocked by #53
  Right-hand slide-in panel with tabs (Overview, Activity, Comments, Attachments, History), header (title + status badges + close), ESC + click-outside to close. URL-synced via `?peek=ENTITY:ID` so peeks are shareable. Dark-mode styled. *Blocks #60.*

- [ ] **#60 Wire DetailDrawer into every list page** — blocked by #58, #59
  Row click opens the peek. Per-entity `DrawerBody` components (InvoiceDetail, OpportunityDetail, CompanyDetail, LeadDetail, TaskDetail, DocumentDetail, VendorDetail…). Comments + Activity tabs wired to existing `/api/comments` + `/api/activity`. The `PresenceStack` built in #50 lands here naturally. *Blocks #63.*

- [ ] **#61 Skeleton loading + rich empty states** — blocked by #53
  `<SkeletonRow>` / `<SkeletonCard>` during RTK Query `isLoading`. `<EmptyState title icon description cta>` replacing every "No X yet" one-liner with icon + description + primary CTA (e.g., "Create your first invoice"). *Blocks #63.*

- [ ] **#62 Global keyboard shortcuts**
  `useHotkeys` hook at `SuiteShell`: `Ctrl+K` focus global search, `n` New on list pages, `/` focus search, `Esc` close peek/modal. ⌨ "Keyboard shortcuts" item in user menu opens cheat-sheet modal. Suppress when input/textarea has focus. *Blocks #63.*

- [ ] **#63 Visual QA + dark-mode audit** — blocked by #58, #60, #61, #62
  Walkthrough every page in both themes. Fix hardcoded whites/grays that don't flip, overflowing numbers, alignment drift, focus rings. Verify Lucide icons inherit `currentColor`. Verify `Ctrl+K` / `Esc` / row-click don't regress existing modals.

---

### Remaining feature work (from Tier-1 roadmap)

- [ ] **#43 Timesheet submission & approval workflow**
  `Timesheet` model grouping `time_entries` by user + week. Submit → approver → approve/reject. Locks entries when approved. Admin UI: my timesheets (submit), inbox (approve). Uses existing `ApprovalRequest` pattern.

- [ ] **#45 2FA / TOTP for admin accounts**
  `totp_secret` + `is_totp_enabled` columns on users. Enrollment endpoint returns provisioning URI. `/auth/login` accepts `totp_code`. Admin settings page to enroll/unenroll. Gate sensitive ops (`admin.*`, `finance.journal.post`) on fresh TOTP verification.

- [ ] **#46 Workspace isolation (multi-tenancy)**
  `workspace_id` FK on every top-level entity (projects, companies, vendors, leads, opps, folders…). Middleware selects active workspace from header. Every query scoped. Admin switches from user menu. Migration fills existing rows with a default workspace.

- [ ] **#48 SSO actual wiring (OIDC callback)**
  `/api/sso/start` redirects to provider, `/api/sso/callback` exchanges code for `id_token`, creates/looks-up user, issues our JWT. Wire to existing `SsoProvider` model. Test with Keycloak / Auth0 preset.

- [ ] **#49 Semantic search + doc Q&A**
  `pgvector` extension, `embedding` column on `document_versions`, compute on upload via OpenAI/local model. `GET /dms/search?semantic=true` does vector search. `POST /dms/qa` retrieves top chunks → LLM → streams answer.

- [ ] **#51 Bank feed integration (Plaid / TrueLayer)**
  Plaid Link flow to connect a bank. Webhook receives transactions → writes to `erp_bank_transactions`. Auto-match runs via existing endpoint. Admin UI: connected banks + sync status.

- [ ] **#52 AI project-plan generation from brief**
  "Describe your project" textarea → Celery task calls LLM → returns WBS (tasks, risks, deliverables, milestones). User reviews + accepts to commit. Uses `reports` Celery queue. Configurable via `LLM_API_KEY`.

---

### Infrastructure (pending)

- [ ] **#10 Put frontend assets behind a CDN**
  Build frontend as static bundle served from CloudFront / Cloudflare. Serve `/assets/*` from CDN, keep `/api/` and `/ws/` on origin. Long cache TTL on hashed asset filenames. Also fixes the 1 MB un-split bundle cold start.

---

## Dependency graph (Track F)

```
#53 ─┬─→ #56 ─────────────────────────┐
     ├─→ #59 ─┐                       │
     └─→ #61 ─┤                       │
              │                       │
#54 ─┬─→ #55  │                       │
     └─→ #57 ─┼─→ #58 ─┬─→ #60 ──┬────┤
              │        │         │    ├─→ #63
              │        └─────────┤    │
              └─→ #62 ───────────┴────┘
```

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

### Collaboration + ops (Tier-1 done)
- [x] #41 Email delivery (SMTP) + Celery queue (password reset, signature requests, approval assignees, expiry reminders, @mention notifications)
- [x] #42 @mentions + notifications drawer (parser + resolve to user_id + Notification rows; SuiteBar popover with unread badge, mark-one/all-read, link navigation)
- [x] #44 Prometheus `/metrics` endpoint + Grafana (provisioned datasource + backend dashboard at `:3001`)
- [x] #47 CSV export everywhere (17 domains via `/api/export/{domain}.csv` + `downloadCsv` helper; Export buttons on Invoices / Expenses / Vendors / Companies / Leads / Opportunities)
- [x] #50 Real-time presence indicators (Redis-backed `/api/presence/*`, `usePresence` hook, `PresenceStack` avatar component — works across replicas)
