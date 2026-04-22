# PMBOK Project Management Platform

A full-stack enterprise business application organized as a **Microsoft 365 / Dynamics 365-style workspace**: one suite shell with an app switcher, surfacing five first-class apps — **Projects**, **Sales (CRM)**, **Finance (ERP)**, **Documents (DMS)**, and **Admin** — plus a separate customer **Portal** for external users. Project management is grounded in **PMBOK 7th Edition**.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (uvicorn, 4 workers, async), SQLAlchemy (async), Python 3.12 |
| Database | PostgreSQL 16 with **pgvector** (semantic search / embeddings) + PgBouncer (transaction pool, `default_pool_size=60`) |
| Cache / Broker / Pub-Sub | Redis 7 — **split** into three dedicated instances (cache / broker / WebSocket pub/sub) |
| Background Jobs | Celery — default queue + dedicated `reports` queue (heavy jobs) + Celery Beat |
| Reverse Proxy | Nginx (rate limiting, gzip, WebSocket upgrade, `least_conn` upstream) |
| Frontend | React 18, Redux Toolkit (RTK Query), TypeScript, Vite |
| Charts | Recharts |
| Auth | JWT (python-jose), bcrypt password hashing, optional **SSO** providers, scoped **API keys** |
| Authorization | Full **ACL**: groups, permissions, user/group associations, explicit deny overrides, project-scoped ACL |
| Real-time | WebSocket per-project rooms with Redis pub/sub fan-out across workers; presence tracking |
| File storage | Pluggable backend — `local` (default) or `s3`-compatible (AWS/MinIO/R2) |
| OCR (optional) | Tesseract + pdf2image for scanned-PDF and image text extraction (env-flag gated) |
| AI / LLM (optional) | OpenAI-compatible endpoint for AI task planner + semantic DocQA (embeddings via pgvector) |
| Payments (optional) | Stripe checkout + webhooks for invoice payment |
| Email / SMS (optional) | SMTP + Twilio SMS |
| Observability | Prometheus `/metrics` + Grafana dashboards, structured JSON request logs, request-id propagation, optional Sentry |
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
- **Customer Portal**: http://localhost/portal
- **Backend API (direct)**: http://localhost:8000/docs (Swagger) — only visible if you uncomment port mapping; by default the backend is network-internal
- **Backend ReDoc**: http://localhost:8000/redoc
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

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
- **Workload & time tracking**, **calendar view**, **resource leveling**
- **Lessons learned**, **change requests**
- **Reports** (summary, schedule, risk, performance) with Excel/PDF export
- **Custom fields** per project attached to tasks / risks / deliverables
- **Project membership** (`ProjectMember`) scoping per-user access to each project
- **AI task planner** (optional LLM): draft a project structure from a prompt; falls back to a heuristic mock when `LLM_API_KEY` is unset
- **Portfolio** view across all projects

### Sales (CRM)
Routes under `/sales/*`, each a dedicated page (no monolithic tabbed page):
- Sales **dashboard** + **forecast** views
- Companies, contacts, interactions (calls, emails, meetings, demos)
- **Leads** with source attribution, scoring, auto-assignment to territories
- **Opportunities** pipeline (Kanban, 6 stages) with forecast and health scoring
- **Quotes** with conversion to **sales orders** and invoices
- **Contracts** with status workflow, MRR / ARR metrics, renewal tracking
- **Campaigns**, campaign members, and **drip sequences** with enrollment
- **Emails**: contact-linked email log with ingest endpoint, templated sends with tracking
- **Commissions** engine (rules, compute, pay) and **territories**
- **Follow-ups** due-today dashboard
- **Health snapshots** computed across all customer accounts

### Finance (ERP)
Routes under `/finance/*`, split Dynamics-style:
- **Chart of Accounts** (24+ seeded), **Cost / Profit Centers**, and **Journal Entries** (post / unpost)
- **Invoices** (AR + AP) with line items, tax, **recurring** templates, **aging** buckets, **credit notes**, payments, **Stripe** pay-button (optional)
- **Returns / RMA** workflow
- **Pricing**: price lists, tiered pricing, discount rules
- **Expenses** with approval workflow
- **Vendors**, **RFQs**, **Requisitions** (convert to POs), **Purchase Orders**, **Goods Receipts** (three-way match)
- **Bank transactions** with auto-matching + manual **reconciliation** tool
- **Multi-currency** with FX rates
- **Inventory**: warehouses, products, stock levels, movements, **batches / lots**, **serial numbers**, **shipments**, **FIFO** costing + barcode panel, reorder reports
- **Assets** with **Depreciation** schedules (run now, accumulated)
- **Budgets** with variance reports
- **Vendor performance** scorecards
- **Reports**: P&L, Balance Sheet, Cash Flow, Tax, Trial Balance

### Documents (DMS)
Routes under `/documents/*` + reports, each a separate page:
- Hierarchical folders, file upload with **version control** + **restore any older version as current**
- **Check-out / check-in locks** to prevent overwrites
- **Full-text search** with advanced filters: date range, author, status, file type
- **Semantic search / Q&A**: pgvector-backed embeddings over document content, asked via `/documents/qa`
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
- **Settings**, **Security** centre (API keys, SSO, sessions)
- **Approvals** inbox (multi-domain)
- **Webhooks** with delivery log and test firings
- **API keys** with scopes + revoke
- **Audit log** / **Activity log** filterable by domain — DMS writes audit entries for every upload / download / view / delete / share / workflow advance
- **Email templates** with tracking (opens, clicks) and admin sends
- **Scheduled reports** (run-due action, routed to `reports` Celery queue)
- **Custom dashboards** (builder with widgets)
- **SSO providers**
- **Workspaces** (multi-tenant scoping; default workspace auto-seeded + backfilled at boot)
- **Tags** (shared taxonomy across projects, CRM, ERP, DMS)
- **Automation**: rule engine (when X happens, do Y) with event triggers
- **Trash**: soft-delete recovery across core entities
- **GDPR**: per-user data export + erase endpoints
- **HR**: employees, leave, attendance, timesheets
- **Access Control** (full sub-app):
  - **Groups** — CRUD + per-group permission matrix editor
  - **Permissions** — browsable catalog of codenames across categories
  - **Users** — group assignments + direct allow/deny overrides per user
  - **Permission Inspector** — pick user + codename + (optional) project → returns full provenance: which group granted, which direct rule applied, project-membership status

### Customer Portal
Separate limited-surface app for external stakeholders at `/portal`:
- Portal login (separate session scope)
- Portal dashboard with the customer's invoices, contracts, quotes, open tickets

## Authorization model

Every write endpoint is gated by `require_permission("<codename>")`. Codenames follow `<app>.<resource>.<action>`, covering Projects, Sales, Finance, Documents, and Admin domains.

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
- **Celery Beat** schedules: nightly `run_retention_task` at 02:00 UTC, nightly `run_expiry_reminders_task` at 01:00 UTC, automation rule sweeper, embedding refresh.
- **Horizontal WebSocket scale**: the `ConnectionManager` (`backend/app/websockets/manager.py`) publishes broadcasts to `redis-ws`; every worker's subscriber fans out to its local connections so backend replicas stay consistent.
- **PgBouncer**: transaction pooling, `max_client_conn=2000`, `default_pool_size=60`, `reserve_pool_size=15`.
- **Read-replica ready**: `READ_DATABASE_URL` env + `get_read_db()` dependency let you point read-only endpoints at a streaming-replicated Postgres. Compose has a `db-replica` service gated behind `--profile replica`.
- **Nginx rate limiting**: 30 r/s general API, 5 r/s auth (brute-force protection), 50 burst; per-user rate-limit middleware on the backend too.
- **Additive migrations**: `app/services/migrations.py` runs `ALTER TABLE … ADD COLUMN IF NOT EXISTS` statements at startup for columns added after initial `create_all()` (no Alembic in use).
- **Startup DDL lock**: replicas coordinate the `create_all()` and additive-migration step via `pg_advisory_xact_lock` so concurrent boots never race.
- **Observability**: Prometheus `/metrics` (latency histograms per handler), Grafana dashboards, JSON access logs with `X-Request-Id` propagation, optional Sentry via `SENTRY_DSN`.
- **Graceful shutdown drain**: in-flight requests get `GRACEFUL_DRAIN_SECONDS` (default 8) to finish before Redis/DB pools are torn down.

## Architecture

```
backend/
  app/
    acl/
      catalog.py       permission catalog (codenames + categories)
      resolver.py      has_permission() + require_permission() FastAPI dependency
      seed.py          idempotent ACL seeding with advisory-lock guard
    models/            SQLAlchemy models (90+ tables across pm / crm / erp / dms / hr / acl / portal / pricing / automation / tags / notification / onboarding)
    routers/           one per domain, permission-gated
      acl.py           ACL admin endpoints + /me/permissions + inspector
      ai_plan.py       LLM-backed project planner
      automation.py    Rule engine CRUD + test-fire
      dashboard.py     Aggregated dashboards
      dms.py / dms_public.py
      email_admin.py   Email templates + tracking admin
      exports.py       CSV / Excel / PDF exports
      gdpr.py          Per-user export + erase
      hr.py            Employees / leave / attendance / timesheets
      portal.py        Customer-portal surface
      presence.py      Who's-online for project rooms
      pricing.py       Price lists + discount rules
      semantic.py      pgvector DocQA + semantic search
      shipping.py      Inventory shipment tracking
      sso.py / stripe_webhooks.py / tags.py / trash.py / onboarding.py / workspaces.py
      (21 other domain routers)
    schemas/           Pydantic request/response schemas
    services/
      audit.py         log_audit() helper writing to AuditEntry
      auth.py          JWT + API-key verification
      automation.py    Rule engine dispatcher
      burndown.py / evm.py / gantt.py / monte_carlo.py / resource_leveling.py / schedule.py  (PM math)
      embeddings.py    pgvector-backed embeddings (OpenAI-compatible)
      llm.py           LLM client wrapper (falls back to heuristic mock)
      email.py / sms.py / pdf_docs.py / stripe_client.py
      storage.py       Pluggable file backend (LocalStorage, S3Storage)
      migrations.py    Idempotent ALTER TABLE runner for startup
      plans.py / pricing.py / webhooks.py / workspaces.py / inventory.py
    websockets/        ConnectionManager + Redis pub/sub fan-out
    celery_app.py      Two queues (default + reports) + Beat schedule
    tasks.py           Monte Carlo + PDF + CSV import tasks
    tasks_dms.py       DMS expiry reminders + retention auto-run
    tasks_ops.py       Ops sweepers (automation, embeddings)
    dependencies.py    Auth dependency (get_current_user, get_current_api_key)
    config.py          Settings via pydantic-settings (split Redis URLs, read-replica URL, storage flags, LLM / Stripe / Sentry / SMS)
    database.py        Async primary + read-replica engines + get_db / get_read_db
    main.py            FastAPI app + lifespan (DDL lock + ACL seed + workspace seed + drain)

frontend/
  src/
    app/               Redux store + hooks
    layouts/           SuiteShell, AppLayout (M365-style shell)
    shell/
      SuiteBar.tsx        Top bar with app switcher, global search, theme, user menu
      AppSwitcher.tsx     Waffle-menu app picker
      AppNav.tsx          App-contextual sidebar (grouped)
      CommandBar.tsx      Reusable command bar (+ New / Edit / Delete / Export / Overflow)
      PageHeader.tsx      Title + subtitle + breadcrumbs + actions
      navConfig.ts        Single source of truth for every app's navigation
      useProjectContext   Hook reading projectId from params OR ?project= query
    pages/
      sales/              17 per-route pages
      finance/            31 per-route pages
      documents/          12 per-route pages (incl. DocQA, Scans, Locks, Annotations)
      admin/              Settings, Security, Activity, Trash, Email templates,
                          ACL sub-app, Tags, Automation, HR sub-app
      portal/             Customer portal (login + dashboard)
      (project-scoped PM pages)
    components/        Reusable components (charts, dnd, Spinner, Toast, …)
    services/
      api.ts           RTK Query slice (all backend endpoints)
      authSlice.ts
      useWebSocket.ts
      wsSlice.ts
    test/              Vitest + Testing Library + MSW tests

nginx/
  nginx.conf         Reverse proxy, rate limits, WebSocket upgrade, gzip, Docker DNS resolver

pgbouncer/
  pgbouncer.ini      Transaction pool (primary + optional read-replica alias)
  userlist.txt       Pool auth

prometheus/          Prometheus scrape config
grafana/             Provisioned dashboards + datasources
```

## API Documentation

FastAPI auto-generates interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**~440 REST endpoints** across 40+ routers + 1 WebSocket endpoint (`/ws/{project_id}`).

## Testing

**734 backend tests** across 43 files — `pytest tests/ -v` runs the full suite.

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

Highlights of the test suite:

- `tests/test_acl.py` — resolver semantics (admin bypass, group grant, deny override, project-scoped membership), endpoints (groups CRUD, /me/permissions, inspector), non-admin 403 enforcement
- `tests/test_dms.py` / `test_dms_new.py` / `test_dms_v2.py` — DMS upload / restore / expiry / share links / folder-permission enforcement / audit-log writes / reports
- `tests/test_crm.py` / `test_crm_v2.py` — pipeline, quotes, contracts, commissions
- `tests/test_erp.py` / `test_erp_v2.py` / `test_inventory_fifo.py` / `test_returns.py` / `test_vendor_performance.py` — ledger, AR/AP, FIFO, RMA, vendor scorecard
- `tests/test_plans.py` / `test_plan_integration.py` — AI planner (with and without LLM configured)
- `tests/test_pricing_discounts.py` — price-list and discount rules
- `tests/test_email_templates_and_tracking.py` — template sends + open/click tracking
- `tests/test_soft_delete_trash.py` — soft-delete + restore across domains
- `tests/test_api_keys_scopes.py` — API-key scope enforcement
- `tests/test_request_id_middleware.py` — observability middleware
- `tests/test_websocket.py` — WebSocket rooms + Redis pub/sub
- `tests/test_hr_tags.py` / `test_onboarding.py` / `test_workspaces.py` — HR, tags, workspace scoping
- `tests/conftest.py` — seeds the permission catalog per test so `require_permission()` works under the admin test user

## Seeding

`backend/seed_fake_data.py` populates 77+ tables with realistic demo data. Run it after the stack is up:

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
- **Wider demo data**: 24 chart-of-accounts entries, 10 journal entries (7 posted), 15 bank transactions, 6 currencies + FX rates, 3 warehouses + 8 products + 40 stock movements, expenses, assets, budgets, depreciation, credit notes, requisitions; DMS folders + 13 docs + 5 templates + signatures + retention policies + workflows + annotations + locks + share links + e-sign providers; 3 webhooks + 3 API keys + 3 scheduled reports + 2 dashboards + 3 SSO providers; 3 workspaces + 8 approvals; HR employees + leave + timesheets; tags + automation rules; ACL group assignments for all admin users + project members across all projects

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
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — production boot refuses the dev default |
| `APP_ENV` | `development` | `production` triggers strict config validation at import time |
| `CORS_ORIGINS` | *(empty)* | Comma-separated allow-list; falls back to `APP_BASE_URL` |
| `REDIS_URL` | `redis://redis-cache:6379/0` | Read-through cache |
| `REDIS_WS_URL` | *(falls back to `REDIS_URL`)* | WebSocket pub/sub fan-out |
| `CELERY_BROKER_URL` | `redis://redis-broker:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis-broker:6379/1` | Celery results |
| `DMS_STORAGE` | `local` | `local` or `s3` — pluggable file backend |
| `DMS_LOCAL_ROOT` | `/app/uploads/dms` | Local storage directory |
| `S3_BUCKET` | *(required when DMS_STORAGE=s3)* | Bucket name |
| `S3_ENDPOINT_URL` | *(unset)* | Custom S3 endpoint (MinIO, R2) |
| `S3_REGION` | `us-east-1` | |
| `DMS_OCR_ENABLED` | *(unset)* | Set to `1` to enable Tesseract OCR for scanned PDFs and images (tesseract + poppler pre-installed in backend image) |
| `LLM_API_KEY` | *(unset)* | Enables AI planner + semantic DocQA. When unset, planner falls back to heuristic mock |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | Model ID |
| `STRIPE_SECRET_KEY` | *(unset)* | Enables "Pay invoice" buttons |
| `STRIPE_WEBHOOK_SECRET` | *(unset)* | Signing secret for `/api/stripe/webhook` |
| `STRIPE_CURRENCY_DEFAULT` | `usd` | |
| `SMS_ENABLED` | `false` | Toggle Twilio SMS |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM` | *(unset)* | Twilio credentials |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_TLS` | *(unset / 587 / tls=true)* | SMTP email |
| `EMAIL_FROM` | `PM Project <no-reply@pmproject.dev>` | Default From address |
| `SENTRY_DSN` | *(unset)* | Enables Sentry — otherwise init is skipped |
| `SENTRY_ENVIRONMENT` | `production` | Sentry environment tag |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Opt-in to performance monitoring |
| `GRACEFUL_DRAIN_SECONDS` | `8` | Max wait for in-flight requests on shutdown |
| `APP_BASE_URL` | `http://localhost` | Used in emails, CORS fallback, share links |
| `VITE_API_URL` | `http://localhost` | Backend URL for frontend |
| `VITE_WS_URL` | `ws://localhost/ws` | WebSocket URL for frontend |

## Roadmap

See [tasks.md](tasks.md) for the historical backlog. The original scaling / page-split / ACL / DMS tracks are all complete; more recent work has added HR, customer portal, AI planner, semantic DocQA, automation rules, email templates with tracking, Stripe checkout, GDPR export/erase, soft-delete trash, inventory batches/serials/shipments, FIFO costing, RMA, and Prometheus + Grafana + Sentry observability.

## License

MIT
