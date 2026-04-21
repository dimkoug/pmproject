# PMBOK Project Management Platform

A full-stack enterprise project management application based on **PMBOK 7th Edition**, with integrated **ERP**, **CRM**, and **Document Management** systems.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL, Python 3.12 |
| Frontend | React 18, Redux Toolkit (RTK Query), TypeScript, Vite |
| Charts | Recharts |
| Auth | JWT (python-jose), bcrypt password hashing |
| Real-time | WebSocket (per-project channels) |
| Infrastructure | Docker Compose, PostgreSQL 16 |

## Quick Start

```bash
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs (Swagger)
- **Backend ReDoc**: http://localhost:8000/redoc

Sign up at the login page to create your first account.

## Features

### Project Management (PMBOK 7th Edition)
- **8 Performance Domains**: Stakeholders, Team, Tasks, Risks, Deliverables, Measurements, Changes, Dashboard
- **CPM / PERT**: Critical path analysis, 3-point estimates, auto-calculated schedule
- **Gantt Chart**: Visual project timeline with critical path highlighting
- **EVM**: Earned Value Management (BAC, PV, EV, AC, CPI, SPI, EAC, ETC, VAC, TCPI)
- **Monte Carlo**: Probabilistic schedule/cost forecasting (100-10,000 iterations)
- **Sprint Planning**: Agile sprint management with velocity tracking
- **Burndown Charts**: Recharts-powered burndown/burnup visualization
- **Schedule Baselines**: Save snapshots and compare actual vs planned
- **Resource Workload**: Team member allocation and utilization tracking
- **Time Tracking**: Log hours per task with timesheet summaries
- **Calendar View**: Tasks and milestones on a timeline
- **Lessons Learned**: Knowledge capture for future projects
- **Reports**: Summary, Schedule, Risk, Performance reports with Excel/PDF export

### ERP System
- Chart of Accounts (asset, liability, equity, revenue, expense)
- Invoices (receivable/payable) with line items and tax
- Expense tracking with approval workflow
- Vendor management
- Purchase Orders with status workflow
- Asset tracking and management
- Financial dashboard (revenue, expenses, profit)

### CRM System
- Company and contact management
- Lead tracking with source attribution
- Opportunity pipeline (Kanban board with 6 stages)
- Interaction logging (calls, emails, meetings, demos)
- CRM dashboard with pipeline value and win rate

### Document Management (DMS)
- Hierarchical folder structure
- File upload with version control
- Document search by title, tags, description
- Status workflow (draft, review, approved, archived)
- Download any version of a document

### Platform Features
- JWT authentication with role-based access (admin, PM, member, viewer)
- Real-time WebSocket updates
- Dark mode toggle
- Global search across all entities
- CSV bulk import
- Excel and PDF export
- Activity audit log
- In-app notifications
- Project templates (save and apply)

## Architecture

```
backend/
  app/
    models/       # SQLAlchemy models (40+ tables)
    routers/      # FastAPI route handlers (19 routers)
    schemas/      # Pydantic request/response schemas
    services/     # Business logic (EVM, CPM/PERT, Monte Carlo, etc.)
    websockets/   # WebSocket connection manager
    dependencies.py  # Auth dependency (get_current_user)
    config.py     # Settings via pydantic-settings
    database.py   # Async engine + session
    main.py       # FastAPI app + router registration

frontend/
  src/
    app/          # Redux store + hooks
    components/   # Reusable components (charts, dnd, Spinner, Toast, etc.)
    pages/        # 30+ page components
    services/     # RTK Query API slice, auth slice, WebSocket slice
    test/         # Vitest + Testing Library + MSW tests
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
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://pmuser:pmpass@db:5432/pmproject` | PostgreSQL connection |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL for frontend |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket URL for frontend |

## License

MIT
