# PMBOK Project Management Platform

A full-stack enterprise business application organized as a **Microsoft 365 / Dynamics 365-style workspace**: one suite shell with an app switcher, surfacing five first-class apps — **Projects**, **Sales (CRM)**, **Finance (ERP)**, **Documents (DMS)**, and **Admin**. Project management is grounded in **PMBOK 7th Edition**.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (uvicorn, 4 workers, async), SQLAlchemy (async), Python 3.12 |
| Database | PostgreSQL 16 + PgBouncer (transaction pool) |
| Cache / Broker / Pub-Sub | Redis 7 (cache, Celery broker, WebSocket pub/sub) |
| Background Jobs | Celery worker + Celery Beat |
| Reverse Proxy | Nginx (rate limiting, gzip, WebSocket upgrade, `least_conn` upstream) |
| Frontend | React 18, Redux Toolkit (RTK Query), TypeScript, Vite |
| Charts | Recharts |
| Auth | JWT (python-jose), bcrypt password hashing |
| Real-time | WebSocket per-project rooms with Redis pub/sub fan-out across workers |
| Infrastructure | Docker Compose |

## Quick Start

```bash
docker-compose up --build
```

- **App** (served through Nginx): http://localhost
- **Backend API (direct)**: http://localhost:8000/docs (Swagger)
- **Backend ReDoc**: http://localhost:8000/redoc

Sign up at the login page to create your first account.

## Workspace Shell

The UI follows the Microsoft 365 / Dynamics 365 pattern:

- **Suite bar** (always on top): brand, app switcher (waffle menu), global search, live WebSocket status, theme toggle, user menu.
- **App switcher**: grid popover to jump between the five apps.
- **App-contextual left nav**: each app has its own grouped sidebar (Overview / Customers / Pipeline / ... for Sales; Receivables / Payables / Ledger / Operations / Reports for Finance; etc.).
- **Project workspace**: drilling into a project swaps the left nav for project-specific tools (Planning / People / Delivery / Analytics) with a **Related** section of deep-links that jump to `/sales`, `/finance`, `/documents` pre-filtered by the current project.
- **Dark mode**: theme toggle in the suite bar; both modes styled end-to-end.

## Apps

### Projects (PMBOK 7th Edition)
- **8 Performance Domains**: Stakeholders, Team, Tasks, Risks, Deliverables, Measurements, Changes, Dashboard
- **CPM / PERT**: critical path analysis, 3-point estimates, auto-calculated schedule
- **Gantt Chart** with critical path highlighting
- **EVM**: BAC, PV, EV, AC, CPI, SPI, EAC, ETC, VAC, TCPI
- **Monte Carlo**: probabilistic schedule/cost forecasting
- **Sprint planning** with velocity tracking; **burndown / burnup** charts
- **Schedule baselines** (save snapshots, compare actual vs planned)
- **Workload & time tracking**, **calendar view**
- **Lessons learned**, **change requests**
- **Reports** (summary, schedule, risk, performance) with Excel/PDF export
- **Portfolio** view across all projects

### Sales (CRM)
- Companies, contacts, interactions (calls, emails, meetings, demos)
- **Leads** with source attribution, scoring, auto-assignment to territories
- **Opportunities** pipeline (Kanban, 6 stages) with forecast and health scoring
- **Quotes** with conversion to invoices
- **Contracts** with status workflow and metrics
- **Campaigns** and drip sequences with email ingestion
- **Commissions** engine (rules, compute, pay) and **territories**
- **Follow-ups** due-today dashboard and account **timeline**

### Finance (ERP)
- **Chart of Accounts** and **Journal Entries** (post / unpost)
- **Invoices** (AR + AP) with line items, tax, recurring templates, aging buckets, credit notes, payments
- **Expenses** with approval workflow
- **Vendors** and **Purchase Orders** with status workflow; **Requisitions** that convert to POs
- **Bank transactions** with auto-matching
- **Inventory**: warehouses, products, stock levels, movements, reorder reports
- **Assets** with **Depreciation** schedules (run now, accumulated)
- **Budgets** with variance reports
- **Reports**: P&L, Balance Sheet, Cash Flow, Tax, Trial Balance

### Documents (DMS)
- Hierarchical folders, file upload with version control, check-out / check-in locks
- **Full-text search** across all documents
- **Digital signatures** with pending / completed tracking
- **Templates** with field-based instantiation
- **Retention policies** with apply-now action
- **Workflows** (step-based approval with advance)
- **Annotations** with resolve flow
- **Virus / content scans** per version

### Admin
- **Approvals** inbox (multi-domain)
- **Webhooks** with delivery log and test firings
- **API keys** with revoke
- **Audit log** filterable by domain
- **Scheduled reports** (run-due action)
- **Custom dashboards** (builder)
- **SSO providers**
- **Workspaces**

## Infrastructure Features

- **Horizontal WebSocket scale**: the `ConnectionManager` (`backend/app/websockets/manager.py`) publishes broadcasts to Redis; every worker's subscriber fans out to its local connections — so backend replicas stay consistent.
- **Nginx rate limiting**: 30 r/s general API, 5 r/s auth (brute-force protection), 50 burst.
- **PgBouncer**: transaction pooling, `max_client_conn=1000`, `default_pool_size=25` (see [tasks.md](tasks.md) for scale-up plan).
- **Gzip + keepalive**: pre-tuned nginx config for production.
- **Dark mode**: first-class, not an afterthought — popovers, tabs, forms all re-themed.

## Architecture

```
backend/
  app/
    models/       SQLAlchemy models (40+ tables)
    routers/      FastAPI route handlers (19 routers)
    schemas/      Pydantic request/response schemas
    services/     Business logic (EVM, CPM/PERT, Monte Carlo, commissions, ...)
    websockets/   ConnectionManager + Redis pub/sub fan-out
    celery_app.py Celery config
    tasks/        Background tasks (reports, recurring invoices, depreciation)
    dependencies.py  Auth dependency (get_current_user)
    config.py     Settings via pydantic-settings
    database.py   Async engine + session
    main.py       FastAPI app + router registration

frontend/
  src/
    app/          Redux store + hooks
    layouts/      SuiteShell, AppLayout (M365-style shell)
    shell/        SuiteBar, AppSwitcher, AppNav, navConfig, useProjectContext
    pages/        Project-scoped pages + ERP/CRM/DMS/Admin (being split per-route)
    components/   Reusable components (charts, dnd, Spinner, Toast, ...)
    services/     RTK Query API slice, auth slice, WebSocket slice
    test/         Vitest + Testing Library + MSW tests

nginx/
  nginx.conf      Reverse proxy, rate limits, WebSocket upgrade, gzip

pgbouncer/
  pgbouncer.ini   Transaction pool config
  userlist.txt    Pool auth
```

## API Documentation

FastAPI auto-generates interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

130+ REST endpoints + 1 WebSocket endpoint (`/ws/{project_id}`).

## Testing

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

## Capacity

Order-of-magnitude on a single 4 vCPU / 8 GB host:

| Definition | Realistic capacity |
|---|---|
| Connected (page open, WS idle) | ~5,000 |
| Active (clicking, ~1 req / 5–10 s) | ~500–1,500 |
| Heavy writes simultaneously | ~100–200 |

With backend scaled to 3 replicas and PgBouncer widened (see [tasks.md](tasks.md) track A): ~20k connected / 3–5k active / ~500 heavy-write.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmproject` | Goes through PgBouncer |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `REDIS_URL` | `redis://redis:6379/0` | Cache + WS pub/sub |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery results |
| `VITE_API_URL` | `http://localhost` | Backend URL for frontend |
| `VITE_WS_URL` | `ws://localhost/ws` | WebSocket URL for frontend |

## Roadmap

See [tasks.md](tasks.md) for the full backlog, organized in three independent tracks:

- **Track A — Scaling** (#6–#11): backend replicas → PgBouncer tuning → Redis split → Celery queues → CDN → read replica.
- **Track B — Page-per-route split** (#12–#16): extract CommandBar/PageHeader, then split CRM / DMS / ERP from monolithic tabbed pages into Dynamics-style per-route pages.
- **Track C — ACL** (#17–#22): proper Groups / Permissions / User Permissions / Group Permissions model with deny overrides, project-scoped ACL, and a "Permission Inspector" admin UI.

## License

MIT
