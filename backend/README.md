# Backend - FastAPI

## Local Development (without Docker)

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://pmuser:pmpass@localhost:5432/pmproject
export SECRET_KEY=dev-secret-key

# Run
uvicorn app.main:app --reload --port 8000
```

## Testing

```bash
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v
```

Tests use SQLite in-memory database (no PostgreSQL required).

## Key Environment Variables

- `DATABASE_URL` - PostgreSQL async connection string
- `SECRET_KEY` - JWT token signing key
- `ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token TTL (default: 1440 = 24h)

## Project Structure

- `app/main.py` - FastAPI app, CORS, router registration, WebSocket endpoint
- `app/models/` - SQLAlchemy models (40+ tables across PM, ERP, CRM, DMS)
- `app/routers/` - API route handlers (19 routers, 130+ endpoints)
- `app/schemas/` - Pydantic validation schemas
- `app/services/` - Business logic (EVM, CPM/PERT, Monte Carlo, burndown, gantt, resource leveling)
- `app/dependencies.py` - `get_current_user` auth dependency
- `app/websockets/` - WebSocket connection manager with per-project channels
