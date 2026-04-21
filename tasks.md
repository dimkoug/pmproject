# Tasks

Three independent tracks. Each track can move in parallel.

---

## Track A — Scaling (ordered, cheapest → most invasive)

- [ ] **#6 Scale backend horizontally via docker compose replicas**
  Add `deploy.replicas` (or `--scale backend=3`) for the backend service. Nginx already uses `least_conn` upstream so no config change needed. Verify WebSockets still work via Redis pub/sub across replicas.

- [ ] **#7 Widen PgBouncer pool and raise Postgres max_connections** — blocked by #6
  In `pgbouncer/pgbouncer.ini` bump `default_pool_size` from 25 → 50–75 and `reserve_pool_size` to 10–15. In `docker-compose.yml` raise Postgres `max_connections` from 200 → 300–400. Measure with `SHOW POOLS` before/after.

- [ ] **#8 Split Redis into three dedicated instances** — blocked by #7
  Split the single Redis into `redis-cache`, `redis-broker` (Celery), `redis-ws` (WebSocket pub/sub) — each with its own `maxmemory` and policy. Update `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` env vars and `app/websockets/manager.py` + `app/cache.py` to point at the right instance.

- [ ] **#9 Scale Celery workers and add a reports queue** — blocked by #8
  Add `celery-worker` replicas in `docker-compose.yml`, create a second worker service bound to a `reports` queue (PDF generation, scheduled reports, depreciation runs, Monte Carlo) so heavy jobs don't block the default queue. Route slow tasks in `app/celery_app.py`.

- [ ] **#10 Put frontend assets behind a CDN** — blocked by #9
  Build the frontend as a static bundle (`vite build`) served from CloudFront / Cloudflare. Serve `/assets/*` from CDN, keep `/api/` and `/ws/` on origin. Long cache TTL on hashed asset filenames. Also fixes the 1 MB un-split bundle cold start.

- [ ] **#11 Add a Postgres read replica for reports and dashboards** — blocked by #10
  Streaming replication from primary. Route read-only endpoints (ERP dashboards, CRM forecast, P&L / Balance Sheet / Cash Flow, portfolio, activity log) to a separate SQLAlchemy engine on the replica. Leave writes on primary. Add a second `[databases]` entry in PgBouncer.

---

## Track B — Page-per-route split (Dynamics-style)

- [ ] **#12 Extract reusable CommandBar and PageHeader components**
  Build the Dynamics-style command bar (`src/shell/CommandBar.tsx` with + New / Edit / Delete / Export / More slots) and a standard `PageHeader` (title + subtitle + actions + breadcrumbs). Every split page will reuse these.

- [ ] **#13 Split CrmPage into per-route pages** — blocked by #12
  Break `src/pages/CrmPage.tsx` (17 tabs, ~1000 lines) into individual pages under `src/apps/sales/pages/`: Dashboard, Companies, Contacts, Leads, Opportunities, Interactions, Quotes, Campaigns, Forecast, FollowUps, Timeline, Emails, Contracts, Commissions, Territories, Drips, Health. Easiest app to start with — no `projectId` coupling.

- [ ] **#14 Split DmsPage into per-route pages** — blocked by #12
  Break `src/pages/DmsPage.tsx` (8 tabs) into individual pages under `src/apps/documents/pages/`: Files, Signatures, Templates, Retention, Locks, Workflows, Annotations, Scans. Each honors the optional `?project=` filter via `useProjectContext()`.

- [ ] **#15 Split ErpPage into per-route pages** — blocked by #12
  Break `src/pages/ErpPage.tsx` (21 tabs, ~560 lines) into individual pages under `src/apps/finance/pages/` — Receivables (Invoices, Recurring, CreditNotes, Aging), Payables (Expenses, Vendors, PurchaseOrders, Requisitions), Ledger (Accounts, Journal, Bank, TrialBalance), Operations (Inventory, Assets, Depreciation, Budgets), Reports (P&L, BalanceSheet, CashFlow, Tax), plus Dashboard. Largest split — save for last.

- [ ] **#16 Remove catch-all :tab routes and delete monolithic pages** — blocked by #13, #14, #15
  Delete `CrmPage.tsx`, `ErpPage.tsx`, `DmsPage.tsx`. Remove `/sales/:tab`, `/finance/:tab`, `/documents/:tab` catch-alls from `App.tsx`. Strip the tab-pill button row from each split page — the sidebar is the nav now.

---

## Track C — ACL (Groups, Permissions, User permissions, Group permissions, ACL management)

- [ ] **#17 Design and implement Permission/Group models + association tables**
  `backend/app/models/acl.py` — `Permission` (codename, name, description, category), `Group` (name, description, is_system). Association tables: `user_groups` (user_id, group_id), `group_permissions` (group_id, permission_id), `user_permissions` (user_id, permission_id, **is_deny**) — the `is_deny` flag supports explicit deny overrides. Alembic migration. Indexes on codename + FKs.

- [ ] **#18 Seed permission catalog and default groups** — blocked by #17
  Derive codenames from every router: `sales.lead.create`, `sales.opportunity.stage_update`, `finance.invoice.post`, `finance.journal.post`, `documents.folder.delete`, `projects.task.update`, `admin.user.manage`, etc. Seed via an Alembic data migration or startup script. Default groups: Admins (all perms), Sales, Finance, Operations, Project Managers, Members, Viewers.

- [ ] **#19 Build permission resolver and FastAPI dependency** — blocked by #17, #18
  `app/acl/resolver.py` — `has_permission(user, codename, *, project_id=None)` unions user.role defaults, group perms, and direct `user_permissions`, with `is_deny` overrides winning. Cache per-request. Expose `require_permission("codename")` FastAPI dependency. Add `/api/me/permissions` so the frontend can hide/disable UI.

- [ ] **#20 Enforce permissions across all routers** — blocked by #19
  Add `require_permission()` to every endpoint in `app/routers/` (projects, tasks, risks, deliverables, crm, erp, dms, admin, webhooks, approvals, ...). Map each to the right codename. 403 on missing perm. Surface 403s clearly in RTK Query. Tests: member/viewer blocked from admin ops.

- [ ] **#21 Add project-scoped ACL (project membership + per-project role)** — blocked by #17
  `project_members` (project_id, user_id, role) — permissions like `projects.task.update` check global perm **and** membership in that specific project. Extend `has_permission()` with `project_id` fallthrough. Ensure related deep-links (e.g. `/finance/invoices?project=X`) respect this — unauthorized users see empty filter, not everyone's data.

- [ ] **#22 Build ACL management UI under Admin app** — blocked by #19, #21, #12
  Pages under `/admin`: **Groups** (list + CRUD + permissions assignment), **Permissions** (read-only browsable catalog grouped by category), **Users** (list + their groups + direct permissions + is_deny overrides), **Permission Inspector** (pick user + codename + optional project → shows exactly which rule granted or denied). Reuse `CommandBar` / `PageHeader` from #12.

---

## Dependency graph

```
Track A:  6 → 7 → 8 → 9 → 10 → 11

Track B:  12 ─┬─→ 13 ─┐
              ├─→ 14 ─┼─→ 16
              └─→ 15 ─┘

Track C:  17 ─┬─→ 18 ─→ 19 ─┬─→ 20
              │              └─→ 22
              └─→ 21 ────────────→ 22
          12 ──────────────────────→ 22
```

## Completed (reference)

- [x] #1 Build SuiteShell and top app bar
- [x] #2 Build AppLayout with contextual sidebar
- [x] #3 Promote CRM/ERP/DMS/Admin to top-level apps
- [x] #4 Relocate Projects under SuiteShell + clean project sidebar
- [x] #5 Add shell CSS and verify visual polish
