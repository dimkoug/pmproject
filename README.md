# PMBOK Project Management Platform

A full-stack enterprise business application organized as a **Microsoft 365 / Dynamics 365-style workspace**: one suite shell with an app switcher, surfacing five first-class apps — **Projects**, **Sales (CRM)**, **Finance (ERP)**, **Documents (DMS)**, and **Admin**. Project management is grounded in **PMBOK 7th Edition**.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (uvicorn, 4 workers, async), SQLAlchemy (async), Python 3.12 |
| Database | PostgreSQL 16 + PgBouncer (transaction pool, `default_pool_size=60`) |
| Cache / Broker / Pub-Sub | Redis 7 — **split** into three dedicated instances (cache / broker / WebSocket pub/sub) |
| Background Jobs | Celery — default queue + dedicated `reports` queue (heavy jobs) + Celery Beat |
| Reverse Proxy | Nginx (rate limiting, gzip, WebSocket upgrade, `least_conn` upstream) |
| Frontend | React 18, Redux Toolkit (RTK Query), TypeScript, Vite |
| Charts | Recharts |
| Auth | JWT (python-jose), bcrypt password hashing |
| Authorization | Full **ACL**: groups, permissions, user/group associations, explicit deny overrides, project-scoped ACL |
| Real-time | WebSocket per-project rooms with Redis pub/sub fan-out across workers |
| File storage | Pluggable backend — `local` (default) or `s3`-compatible (AWS/MinIO/R2) |
| OCR (optional) | Tesseract + pdf2image for scanned-PDF and image text extraction (env-flag gated) |
| Infrastructure | Docker Compose (backend replicas `deploy.replicas: 2`; optional Postgres read replica profile) |

## Quick Start

```bash
docker compose up --build

# Promote the first admin (one-off, required for admin-gated endpoints):
docker compose exec db psql -U pmuser -d pmproject \
  -c "UPDATE users SET role='ADMIN' WHERE email='you@example.com';"

# Seed realistic data for demos (see "Seeding" section below):
cd backend && python seed_fake_data.py --base-url http://localhost
```

- **App** (served through Nginx): http://localhost
- **Backend API (direct)**: http://localhost:8000/docs (Swagger) — only visible if you uncomment port mapping; by default the backend is network-internal
- **Backend ReDoc**: http://localhost:8000/redoc

Sign up at the login page to create your first account.

## Workspace Shell

The UI follows the Microsoft 365 / Dynamics 365 pattern:

- **Suite bar** (always on top): brand, app switcher (waffle menu), global search, live WebSocket status, theme toggle, user menu.
- **App switcher**: grid popover to jump between the five apps.
- **App-contextual left nav**: each app has its own grouped sidebar (Overview / Customers / Pipeline / ... for Sales; Receivables / Payables / Ledger / Operations / Reports for Finance; etc.).
- **Project workspace**: drilling into a project swaps the left nav for project-specific tools (Planning / People / Delivery / Analytics) with a **Related** section of deep-links that jump to `/sales`, `/finance`, `/documents` pre-filtered by the current project.
- **CommandBar** + **PageHeader** reusable shell components drive consistent page chrome (`+ New / Edit / Delete / Export / ⋯`).
- **Dark mode**: first-class, theme toggle in the suite bar; popovers, tabs, forms, charts, command bars all re-themed.

## Apps

### Projects (PMBOK 7th Edition)
- **8 Performance Domains**: Stakeholders, Team, Tasks, Risks, Deliverables, Measurements, Changes, Dashboard
- **CPM / PERT**: critical path analysis, 3-point estimates, auto-calculated schedule
- **Gantt Chart** with critical path highlighting
- **EVM**: BAC, PV, EV, AC, CPI, SPI, EAC, ETC, VAC, TCPI
- **Monte Carlo**: probabilistic schedule/cost forecasting (offloaded to Celery `reports` queue)
- **Sprint planning** with velocity tracking; **burndown / burnup** charts
- **Schedule baselines** (save snapshots, compare actual vs planned)
- **Workload & time tracking**, **calendar view**
- **Lessons learned**, **change requests**
- **Reports** (summary, schedule, risk, performance) with Excel/PDF export
- **Custom fields** per project attached to tasks / risks / deliverables
- **Project membership** (`ProjectMember`) scoping per-user access to each project
- **Portfolio** view across all projects

### Sales (CRM)
17 routes under `/sales/*`, each now a dedicated page (no monolithic tabbed page):
- Companies, contacts, interactions (calls, emails, meetings, demos)
- **Leads** with source attribution, scoring, auto-assignment to territories
- **Opportunities** pipeline (Kanban, 6 stages) with forecast and health scoring
- **Quotes** with conversion to invoices
- **Contracts** with status workflow, MRR / ARR metrics, renewal tracking
- **Campaigns**, campaign members, and **drip sequences** with enrollment
- **Emails**: contact-linked email log with ingest endpoint
- **Commissions** engine (rules, compute, pay) and **territories**
- **Follow-ups** due-today dashboard
- **Health snapshots** computed across all customer accounts

### Finance (ERP)
21 routes under `/finance/*`, split Dynamics-style:
- **Chart of Accounts** (24+ seeded) and **Journal Entries** (post / unpost)
- **Invoices** (AR + AP) with line items, tax, recurring templates, aging buckets, credit notes, payments
- **Expenses** with approval workflow
- **Vendors** and **Purchase Orders** with status workflow; **Requisitions** that convert to POs
- **Bank transactions** with auto-matching
- **Multi-currency** with FX rates
- **Inventory**: warehouses, products, stock levels, movements, reorder reports
- **Assets** with **Depreciation** schedules (run now, accumulated)
- **Budgets** with variance reports
- **Reports**: P&L, Balance Sheet, Cash Flow, Tax, Trial Balance

### Documents (DMS)
8 routes under `/documents/*` + 2 reports, each a separate page:
- Hierarchical folders, file upload with **version control** + **restore any older version as current**
- **Check-out / check-in locks** to prevent overwrites
- **Full-text search** with advanced filters: date range, author, status, file type
- **Document expiry dates** + "expiring soon" widget + nightly Celery reminder task (creates `Notification` rows)
- **Digital signatures** with pending / completed tracking
- **Templates** with field-based instantiation
- **Retention policies** — manual apply + nightly Celery auto-run
- **Workflows** (step-based approval with advance)
- **Annotations** with resolve flow
- **Virus / content scans** per version
- **Shareable public links** with expiry + revoke; public `/api/dms/share/{token}` unauth endpoint
- **Folder-level ACL** enforced on list / read / download — private folders invisible to non-members
- **Entity links** — attach docs to CRM opportunities, projects, etc.
- **DMS reports**: Usage (top users, top downloaded docs), Pending approvals, Audit export

### Admin
- **Approvals** inbox (multi-domain)
- **Webhooks** with delivery log and test firings
- **API keys** with revoke
- **Audit log** filterable by domain — **DMS writes audit entries** for every upload / download / view / delete / share / workflow advance
- **Scheduled reports** (run-due action, routed to `reports` Celery queue)
- **Custom dashboards** (builder with widgets)
- **SSO providers**
- **Workspaces**
- **Access Control** (full sub-app):
  - **Groups** — CRUD + per-group permission matrix editor
  - **Permissions** — browsable catalog of 58 codenames across 5 categories
  - **Users** — group assignments + direct allow/deny overrides per user
  - **Permission Inspector** — pick user + codename + (optional) project → returns full provenance: which group granted, which direct rule applied, project-membership status

## Authorization model

Every write endpoint is gated by `require_permission("<codename>")`. Codenames follow `<app>.<resource>.<action>`:

- **projects.\*** — `project.create/update/delete`, `task.create/update/delete`, `risk/deliverable/change.manage`, `reports.view`
- **sales.\*** — `company.manage`, `lead.create/update_status`, `opportunity.manage`, `quote.manage`, `contract.manage`, `campaign.manage`, `commission.manage`, `territory.manage`
- **finance.\*** — `invoice.create/update_status`, `payment.record`, `expense.manage`, `vendor.manage`, `po.manage`, `requisition.manage`, `asset.manage`, `account.manage`, `journal.post`, `bank.manage`, `inventory.manage`, `budget.manage`, `reports.view`
- **documents.\*** — `folder.manage`, `file.upload/download/delete`, `signature.manage`, `workflow.manage`, `retention.manage`
- **admin.\*** — `user.manage`, `group.manage`, `permission.assign`, `approval.decide`, `webhook.manage`, `apikey.manage`, `audit.view`, `sso.manage`, `workspace.manage`

Resolution rules (implemented in `app/acl/resolver.py`):

1. `role=ADMIN` gets every codename (blanket grant).
2. Otherwise codenames are collected from group memberships (`user_groups` + `group_permissions`).
3. Direct `user_permissions` rows with `is_deny=False` add grants; rows with `is_deny=True` **override** everything above.
4. When the codename carries `project_id` and starts with `projects.*`, the user must also be a `ProjectMember` (admins bypass).

Per-request memoization prevents repeated DB lookups. The catalog auto-seeds at startup (idempotent, guarded by a Postgres advisory lock so concurrent replicas don't race).

7 default system groups ship preseeded: **Admins** (all), **Project Managers**, **Members**, **Viewers**, **Sales**, **Finance**, **Operations**.

## Infrastructure Features

- **Horizontal scaling**: backend runs `deploy.replicas: 2` by default; nginx uses `least_conn` upstream. Scale further with `docker compose up --scale backend=N`.
- **Three Redis instances** — `redis-cache` (LRU, 512 MB), `redis-broker` (no-evict, 256 MB for Celery), `redis-ws` (128 MB for WebSocket pub/sub) — so flood traffic on one tier doesn't evict another.
- **Two Celery worker pools**: default queue for lightweight async work; `reports` queue with separate worker service for heavy jobs (Monte Carlo, PDF generation, nightly retention, expiry reminders, scheduled reports, depreciation runs).
- **Celery Beat** schedules: nightly `run_retention_task` at 02:00 UTC, nightly `run_expiry_reminders_task` at 01:00 UTC.
- **Horizontal WebSocket scale**: the `ConnectionManager` (`backend/app/websockets/manager.py`) publishes broadcasts to `redis-ws`; every worker's subscriber fans out to its local connections so backend replicas stay consistent.
- **PgBouncer**: transaction pooling, `max_client_conn=2000`, `default_pool_size=60`, `reserve_pool_size=15`.
- **Read-replica ready**: `READ_DATABASE_URL` env + `get_read_db()` dependency let you point read-only endpoints at a streaming-replicated Postgres. Compose has a `db-replica` service gated behind `--profile replica`.
- **Nginx rate limiting**: 30 r/s general API, 5 r/s auth (brute-force protection), 50 burst.
- **Additive migrations**: `app/services/migrations.py` runs `ALTER TABLE … ADD COLUMN IF NOT EXISTS` statements at startup for columns added after initial `create_all()` (no Alembic in use).
- **Startup DDL lock**: replicas coordinate the `create_all()` and additive-migration step via `pg_advisory_xact_lock` so concurrent boots never race.

## Architecture

```
backend/
  app/
    acl/
      catalog.py      58-codename permission catalog
      resolver.py     has_permission() + require_permission() FastAPI dependency
      seed.py         idempotent ACL seeding with advisory-lock guard
    models/           SQLAlchemy models (70+ tables)
    routers/
      acl.py          ACL admin endpoints + /me/permissions + inspector
      dms_public.py   Unauthenticated public share-link endpoint
      (21 others)     One per domain, permission-gated
    schemas/          Pydantic request/response schemas
    services/
      audit.py        log_audit() helper writing to AuditEntry
      storage.py      Pluggable file backend (LocalStorage, S3Storage)
      migrations.py   Idempotent ALTER TABLE runner for startup
      (business logic — EVM, CPM/PERT, Monte Carlo, commissions, …)
    websockets/       ConnectionManager + Redis pub/sub fan-out
    celery_app.py     Two queues (default + reports) + Beat schedule
    tasks.py          Monte Carlo + PDF + CSV import tasks
    tasks_dms.py      DMS expiry reminders + retention auto-run
    dependencies.py   Auth dependency (get_current_user)
    config.py         Settings via pydantic-settings (split Redis URLs, read-replica URL, storage flags)
    database.py       Async primary + read-replica engines + get_db / get_read_db
    main.py           FastAPI app + lifespan (DDL lock + ACL seed)

frontend/
  src/
    app/              Redux store + hooks
    layouts/          SuiteShell, AppLayout (M365-style shell)
    shell/
      SuiteBar.tsx       Top bar with app switcher, global search, theme, user menu
      AppSwitcher.tsx    Waffle-menu app picker
      AppNav.tsx         App-contextual sidebar (grouped)
      CommandBar.tsx     Reusable command bar (+ New / Edit / Delete / Export / Overflow)
      PageHeader.tsx     Title + subtitle + breadcrumbs + actions
      navConfig.ts       Single source of truth for every app's navigation
      useProjectContext  Hook reading projectId from params OR ?project= query
    pages/
      sales/          16 per-route pages
      finance/        21 per-route pages
      documents/      8 library pages + 2 report pages
      admin/          Settings + ACL sub-app (Groups, Permissions, Users, Inspector)
      (project-scoped PM pages)
    components/       Reusable components (charts, dnd, Spinner, Toast, …)
    services/
      api.ts          RTK Query slice (130+ endpoints + every ACL / DMS new endpoint)
      authSlice.ts
      useWebSocket.ts
      wsSlice.ts
    test/             Vitest + Testing Library + MSW tests

nginx/
  nginx.conf        Reverse proxy, rate limits, WebSocket upgrade, gzip, Docker DNS resolver

pgbouncer/
  pgbouncer.ini     Transaction pool (primary + optional read-replica alias)
  userlist.txt      Pool auth
```

## API Documentation

FastAPI auto-generates interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**317 REST endpoints** + 1 WebSocket endpoint (`/ws/{project_id}`).

## Testing

60 backend tests — `pytest tests/ -v` runs the full suite.

```bash
# Backend (pytest)
cd backend
pip install -r requirements.txt
pytest tests/ -v

# Frontend (vitest)
cd frontend
npm install
npm test

# Type-check frontend
npx tsc --noEmit

# Production build (validates the whole bundle)
npx vite build
```

Key test files:

- `tests/test_acl.py` — 14 tests: resolver semantics (admin bypass, group grant, deny override, project-scoped membership), endpoints (groups CRUD, /me/permissions, inspector), non-admin 403 enforcement
- `tests/test_dms_new.py` — 21 tests: restore version, expiry window, advanced search filters, share link flow (create/list/revoke/public-download/expired/invalid), folder-permission enforcement, audit-log writes, reports
- `tests/conftest.py` — seeds the 58-permission catalog per test so `require_permission()` works under the admin test user

## Seeding

`backend/seed_fake_data.py` populates 77 tables with realistic demo data. Run it after the stack is up:

```bash
cd backend
python seed_fake_data.py --base-url http://localhost                # everything
python seed_fake_data.py --no-small                                 # skip the 3 small software projects
python seed_fake_data.py --no-large                                 # skip construction/stadium/banking
python seed_fake_data.py --no-enterprise                            # skip Microsoft/SAP/Oracle/... CRM+ERP
python seed_fake_data.py --no-wider                                 # skip DMS content, ERP ledger, Admin cross-cutting
```

What gets populated:

- **3 small software projects** — legacy CRM migration, smart factory IoT, digital banking app (per-project: team, tasks with 3-point estimates, risks, deliverables, measurements, change requests, dependencies, sprints, comments, lessons, time entries)
- **3 large projects** with domain-rich templates:
  - **Meridian One** — $280M, 40-storey office tower construction (56 tasks across Pre-construction → Commissioning & Handover)
  - **Aurora Park** — $1.2B, 75,000-seat football stadium with retractable roof (60 tasks)
  - **Helios** — $180M, 30-month core banking platform modernization (82 tasks)
- **28 enterprise CRM companies** — Microsoft, SAP, Oracle, Salesforce, Google Cloud, AWS, IBM, Adobe, ServiceNow, Workday, Siemens, Accenture, Cisco, Dell, HPE, VMware, Atlassian, Snowflake, Databricks, Red Hat, Intel, NVIDIA, Nokia, BT, Infosys, TCS, Capgemini, T-Systems — with 204 contacts, 60 opportunities, 420 interactions, quotes, contracts, 12 campaigns, 5 drip sequences, territories, commissions rules, health snapshots
- **25 ERP vendors** — AWS, Azure, GCP, Okta, Datadog, Cloudflare, GitHub, Snowflake, Stripe, Twilio, Slack, Atlassian, PagerDuty, Splunk, New Relic, Elastic, MongoDB, HashiCorp, Zoom, Adobe, LinkedIn, Gartner, Forrester, Cisco, Tableau — with 72 POs, 46 AP invoices, 15 AR invoices, 10 payments
- **Wider demo data**: 24 chart-of-accounts entries, 10 journal entries (7 posted), 15 bank transactions, 6 currencies + FX rates, 3 warehouses + 8 products + 40 stock movements, expenses, assets, budgets, depreciation, credit notes, requisitions; DMS folders + 13 docs + 5 templates + signatures + retention policies + workflows + annotations + locks + share links + e-sign providers; 3 webhooks + 3 API keys + 3 scheduled reports + 2 dashboards + 3 SSO providers; 3 workspaces + 8 approvals; ACL group assignments for all admin users + project members across all projects

The seeder is idempotent for safely re-running the wider-data section; it signs up a dedicated `seed-admin@pmproject.dev` user and promotes it to ADMIN via `docker compose exec db psql`.

## Capacity

Order-of-magnitude on a single 4 vCPU / 8 GB host:

| Definition | Realistic capacity |
|---|---|
| Connected (page open, WS idle) | ~5,000 |
| Active (clicking, ~1 req / 5–10 s) | ~500–1,500 |
| Heavy writes simultaneously | ~100–200 |

With backend scaled to 3 replicas and PgBouncer widened (see [tasks.md](tasks.md)): ~20k connected / 3–5k active / ~500 heavy-write.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmproject` | Primary via PgBouncer |
| `READ_DATABASE_URL` | *(unset)* | If set, read-only endpoints route here (compose gates `db-replica` behind `--profile replica`) |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `REDIS_URL` | `redis://redis-cache:6379/0` | Read-through cache |
| `REDIS_WS_URL` | *(falls back to `REDIS_URL`)* | WebSocket pub/sub fan-out |
| `CELERY_BROKER_URL` | `redis://redis-broker:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis-broker:6379/1` | Celery results |
| `DMS_STORAGE` | `local` | `local` or `s3` — pluggable file backend |
| `DMS_LOCAL_ROOT` | `/app/uploads/dms` | Local storage directory |
| `S3_BUCKET` | *(required when DMS_STORAGE=s3)* | Bucket name |
| `S3_ENDPOINT_URL` | *(unset)* | Custom S3 endpoint (MinIO, R2) |
| `S3_REGION` | `us-east-1` | |
| `DMS_OCR_ENABLED` | *(unset)* | Set to `1` to enable Tesseract OCR for scanned PDFs and images (requires `tesseract-ocr` + `poppler-utils` in backend image — pre-installed) |
| `VITE_API_URL` | `http://localhost` | Backend URL for frontend |
| `VITE_WS_URL` | `ws://localhost/ws` | WebSocket URL for frontend |

## Roadmap

See [tasks.md](tasks.md) for the historical backlog. All four original tracks are complete except CDN hosting:

- ✅ **Track A — Scaling** (#6–#11): backend replicas, PgBouncer tuning, Redis split, Celery queues, read replica. *(Only CDN #10 remains.)*
- ✅ **Track B — Page-per-route split** (#12–#16): CommandBar/PageHeader extracted; all three monolithic tabbed pages split into 16 / 21 / 8 per-route pages.
- ✅ **Track C — ACL** (#17–#22): models + resolver + enforcement + project-scoped ACL + admin UI shipped.
- ✅ **Track D — DMS gap closure** (#23–#32): folder-permission enforcement, audit log, restore version, advanced search, expiry + reminders, retention auto-run, OCR, share links, pluggable storage, reports.
- ✅ **Track E — DMS UI surfacing** (#33–#38): expiry input + widget, restore button, share dialog, search filters, reports pages, folder permissions editor.
- ✅ **Tests** (#39): 60 tests covering ACL, DMS additions, and existing routes.
- ✅ **Seed** (#40): `seed_fake_data.py` now covers 77 tables with realistic domain data.

## License

MIT
