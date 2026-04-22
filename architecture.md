# Architecture

This document describes how the codebase is organised and how requests flow
through it. Read [`README.md`](README.md) first if you want the *what*; this
document focuses on the *how* and the *why* — enough that a new contributor
can pick up any subsystem without spelunking.

## Table of contents

1. [Service topology](#service-topology)
2. [Backend layout](#backend-layout)
3. [Frontend layout](#frontend-layout)
4. [Data model overview](#data-model-overview)
5. [Cross-cutting concerns](#cross-cutting-concerns)
6. [Request lifecycle](#request-lifecycle)
7. [Background jobs](#background-jobs)
8. [Real-time + presence](#real-time--presence)
9. [Extension points](#extension-points)
10. [Observability + ops](#observability--ops)
11. [Where to start when adding things](#where-to-start-when-adding-things)

---

## Service topology

Everything runs under one `docker compose up`. Thirteen services:

```
                ┌─────────────────────┐
  browsers ───▶ │  nginx :80          │  rate limit, gzip, ws upgrade,
                │  (least_conn)       │  /assets/* immutable cache
                └──┬─────────┬────────┘
                   │         │
                   ▼         ▼
           ┌──────────┐  ┌────────────┐
           │ frontend │  │ backend ×N │  uvicorn, async FastAPI
           │ Vite dev │  │ workers=4  │  ── advisory-locked DDL on boot
           └──────────┘  └─────┬──────┘
                               │
              ┌────────────────┼─────────────────┐
              ▼                ▼                 ▼
        ┌────────┐      ┌─────────────┐    ┌──────────┐
        │pgbouncer│ ──▶ │pgvector/pg16│    │ redis ×3 │
        │ pool=60 │     │ primary +   │    │ cache    │
        └─────────┘     │ optional    │    │ broker   │
                        │ replica     │    │ ws       │
                        └─────────────┘    └──────────┘
                                                ▲
                                                │
                ┌────────────────┬──────────────┴──────┐
                ▼                ▼                     ▼
         ┌────────────┐   ┌──────────────┐    ┌──────────────┐
         │ celery ×N  │   │celery-reports│    │  celery-beat │
         │ default q  │   │ heavy jobs   │    │  cron        │
         └────────────┘   └──────────────┘    └──────────────┘

                + Prometheus :9090, Grafana :3001 (provisioned)
```

**Why three Redises.** Cache eviction (LRU, 512 MB) shouldn't drop pending
Celery tasks; WebSocket pub/sub flood shouldn't push out cache hits. Each
tier gets its own instance with its own memory policy.

**Why two Celery queues.** A 60-second Monte Carlo run shouldn't block the
60-millisecond email enqueue. The `reports` queue runs on a dedicated worker
so a stuck heavy job can never starve the rest.

**Why backend replicas + advisory locks.** Two backend pods boot
simultaneously. Both want to run `Base.metadata.create_all` and the additive
migrations. They use `pg_advisory_lock` (different keys per phase) to
serialise — the second pod waits, then no-ops. Without this, concurrent
`CREATE INDEX IF NOT EXISTS` can race the existence check against the
catalog insert and hit `pg_class_relname_nsp_index` unique-violations.

**Why pgbouncer.** The async backend can hold thousands of idle client
connections cheaply, but each must map to a real Postgres backend. The pool
limits real connections (`default_pool_size=60`) so we don't exhaust
Postgres `max_connections` at scale.

---

## Backend layout

```
backend/app/
├── main.py             FastAPI app + lifespan (DDL lock, ACL seed,
│                       workspace seed), router mounting, CORS, /metrics
├── config.py           pydantic-settings, all env vars in one place
├── database.py         async primary + read-replica engines + get_db /
│                       get_read_db dependencies
├── dependencies.py     get_current_user (JWT decode + load)
├── celery_app.py       broker, two queues, beat schedule
├── tasks.py            Celery tasks (Monte Carlo, PDF, CSV import, AI plan)
├── tasks_dms.py        DMS expiry reminders + retention auto-run
├── cache.py            Redis cache helpers + lifecycle
├── websockets/
│   └── manager.py      ConnectionManager + Redis pub/sub fan-out across
│                       backend replicas
├── acl/
│   ├── catalog.py      Single source of truth for every codename + default
│   │                   group → permission map (~80 codenames now)
│   ├── seed.py         Idempotent seeder (advisory-locked) — also seeds
│   │                   default field masks (#77)
│   └── resolver.py     has_permission(), require_permission() FastAPI
│                       dependency, get_field_mask(), apply_field_mask()
├── services/
│   ├── audit.py        log_audit() — also fires automation events (#72)
│   ├── automation.py   IFTTT-style rule evaluator
│   ├── auth.py         password hash + JWT mint
│   ├── email.py        SMTP via Celery (with no-op fallback)
│   ├── sms.py          Twilio adapter via Celery (with no-op fallback)
│   ├── stripe_client.py  REST adapter via httpx (no SDK dep)
│   ├── llm.py          OpenAI-compatible chat completions (mock fallback)
│   ├── embeddings.py   OpenAI-compatible embeddings (mock fallback) +
│   │                   chunker
│   ├── workspaces.py   get_active_workspace_id() resolver + seed/backfill
│   ├── storage.py      LocalStorage / S3Storage adapters (DMS_STORAGE flag)
│   ├── monte_carlo.py  Probabilistic schedule/cost simulator
│   ├── evm.py          Earned-value calculations
│   ├── schedule.py     CPM / PERT
│   ├── gantt.py        Gantt projection
│   ├── burndown.py
│   ├── resource_leveling.py
│   └── migrations.py   Additive ALTER TABLE / CREATE INDEX runner with
│                       per-statement transactions + advisory lock
├── routers/            One file per domain — register in main.py
└── models/             SQLAlchemy 2.0-style declarative models
    └── __init__.py     Single import surface for Alembic-free metadata
```

Routers are organised by **domain**, not by HTTP verb. A typical router file
holds the Pydantic schemas inline, the CRUD handlers, and any
domain-specific reports. Cross-cutting things (audit, ACL, workspaces,
field-masks) live in `services/` and `acl/` so routers just call them.

**Models use SQLAlchemy 2.0 typed-mapping syntax** (`Mapped[]`,
`mapped_column`). All async via `asyncpg`. No ORM relationships are
configured for the cross-domain links — endpoints fetch related rows
explicitly via `select(...)`. This is intentional: avoids accidental N+1s
from autoload, and keeps query shape obvious in code review.

**Portable column types** — for tests we run against sqlite (faster,
ephemeral). Postgres-only types (`JSONB`, `ARRAY`, `Vector`) are wrapped:

```python
PortableJSON      = JSON().with_variant(JSONB(), "postgresql")
PortableStringList= JSON().with_variant(ARRAY(String(64)), "postgresql")
_EMBED_TYPE       = JSON().with_variant(Vector(1536), "postgresql")
```

Production gets the optimal types; sqlite-backed tests get something
`create_all` can compile.

---

## Frontend layout

```
frontend/src/
├── main.tsx               Bootstrap: i18n, store, router, error boundary
├── App.tsx                Route table — auth pages + SuiteShell-wrapped
│                          app routes + customer-portal pages (separate auth)
├── app/
│   ├── store.ts           Redux store (RTK)
│   └── hooks.ts           useAppDispatch, useAppSelector
├── i18n/
│   ├── index.ts           react-i18next init
│   ├── en.json            seed catalog (common / shell / apps / nav)
│   └── format.ts          useFormat() — formatDate / formatCurrency / …
│                          honours user.timezone + user.language
├── layouts/
│   ├── SuiteShell.tsx     The "office 365" chrome — SuiteBar + Outlet +
│   │                      DetailDrawer + ModalHost
│   └── AppLayout.tsx      Per-app left nav + main content area
├── shell/                 Reusable cross-app components
│   ├── icons.ts           Lucide icon registry (curated 70 icons)
│   ├── SuiteBar.tsx       Top bar: app switcher, search, theme toggle,
│   │                      notifications, user menu (density / language /
│   │                      timezone / notifications / 2FA / data export /
│   │                      workspace switcher)
│   ├── AppSwitcher.tsx    Waffle-menu app picker
│   ├── AppNav.tsx         App-contextual sidebar
│   ├── navConfig.ts       Single source of truth for app navigation
│   ├── CommandBar.tsx     +/Edit/Delete/Export/⋯ bar with auto-`n` hotkey
│   ├── PageHeader.tsx     Title + subtitle + breadcrumbs + actions
│   ├── DataTable.tsx      TanStack Table wrapper — sort/filter/search/
│   │                      sticky/pagination/selection/skeletons/empty
│   ├── DetailDrawer.tsx   Right side-peek synced via ?peek=ENTITY:ID
│   ├── drawerBodyRegistrations.tsx   Per-entity drawer renderers
│   ├── drawerTabs.tsx     Reusable Comments / Activity / OverviewGrid
│   ├── FormModal.tsx      Title + fields + cancel/primary + ESC + focus trap
│   ├── modalService.tsx   Imperative promptForValues / confirmAction /
│   │                      notifyUser — replaces native prompt()/alert()
│   ├── Skeleton.tsx       SkeletonRow / SkeletonCard / SkeletonTable
│   ├── EmptyState.tsx     Icon + description + CTA
│   ├── TagChip.tsx        Colored pill with optional remove ×
│   ├── TagPicker.tsx      Combobox attach/detach UI; auto-mounts in drawer
│   ├── useHotkeys.ts      Global keyboard shortcut hook (Ctrl+K, /, n, ?)
│   ├── ShortcutsCheatsheet.tsx
│   ├── PresenceStack.tsx  Live "who's here" avatar stack
│   └── usePresence.ts
├── pages/
│   ├── sales/             16 routes — Companies, Contacts, Leads,
│   │                      Opportunities, Quotes, SalesOrders, Contracts,
│   │                      Campaigns, Drips, Emails, Interactions,
│   │                      FollowUps, Commissions, Territories, Health
│   ├── finance/           21 routes — Invoices, Expenses, Vendors, POs,
│   │                      Requisitions, GRN, RFQs, Assets, Accounts,
│   │                      Centers, Journal, Bank, Reconciliation,
│   │                      Inventory, Batches, Serials, Shipments,
│   │                      Budgets, CreditNotes, Recurring, Aging,
│   │                      Depreciation + report pages
│   ├── documents/         Files, Q&A, Signatures, Templates, Workflows,
│   │                      Retention, Locks, Annotations, Scans + reports
│   ├── admin/             Settings + ACL sub-app + Tags + Automation +
│   │                      HR (Employees / Leave / Attendance /
│   │                      Timesheets / Overview) + Security
│   ├── portal/            Customer-facing — separate auth (magic-link →
│   │                      portal-scoped JWT)
│   └── (project-scoped PM pages)
├── components/            Domain UI bits — charts, dnd, Toast, ErrorBoundary,
│                          AiPlanModal
└── services/
    ├── api.ts             Single RTK Query slice — ~200 endpoints. Header
    │                      injection: Authorization + X-Workspace-Id
    ├── authSlice.ts       token + user (timezone / language / phone /
    │                      notify_email / notify_sms / is_totp_enabled)
    ├── useWebSocket.ts    Per-project websocket hook
    └── wsSlice.ts
```

**One RTK Query slice for everything.** Means one fetch baseUrl, one
prepareHeaders, one cache invalidation graph. ~200 endpoints. Tag-based
invalidation for write paths. The user-menu workspace switcher dispatches
`apiSlice.util.resetApiState()` so every cached list refetches under the
new tenant scope.

**SuiteShell + AppLayout** is the M365 / Dynamics 365 pattern: one suite
chrome with an app switcher, then each app has its own contextual left nav.
A project workspace swaps the left nav for project-specific tools.

**Detail drawer is URL-synced** (`?peek=ENTITY:ID`). Means peeks are
shareable, back-button-friendly, and survive reloads. Per-entity body
renderers live in `drawerBodyRegistrations.tsx`.

**FormModal infrastructure replaced 143 native `prompt`/`alert`/`confirm`
calls** across 38 pages during the Track-F refactor. The imperative API
(`promptForValues`, `confirmAction`, `notifyUser`) lets pages await a modal
result without manual mounting.

---

## Data model overview

70+ tables, organised by domain (`backend/app/models/<domain>.py`). Key
relationships:

```
       ┌─────┐         ┌──────────┐          ┌──────────┐
       │ User│─────────│Workspace │──────────│Membership│
       └──┬──┘         │ (tenant) │          └──────────┘
          │            └────┬─────┘
          │                 │ workspace_id (nullable on flagship tables)
          ▼                 ▼
   ┌─────────┐       ┌──────────┐    ┌─────────┐    ┌────────┐
   │ Project │─...──▶│ Company  │   │ Vendor  │    │ Tag    │
   └────┬────┘       └─────┬────┘    └────┬────┘    └────┬───┘
        │                  │              │              │
   ┌────┼─────┬───────┐    │              │              │ via
   ▼    ▼     ▼       ▼    ▼              ▼              ▼ tag_links
 Task Risk Deliv. Lesson  Lead → Opp → Quote ──▶ SalesOrder ──▶ Invoice ──▶ Payment
                                                                  ▲
                                                            from Stripe webhook
        │
        ▼
  Sprint, ChangeRequest, ScheduleBaseline, TimeEntry, Timesheet
                                                ▲
                                                │ groups by week
                                                Approval → Lock entries

                            POs ──▶ GRN ──▶ StockMovement
                              ▲              ▲
                            from              ├─ Batch / Serial tracking
                            Requisition       │
                              ▲               │
                            from              │ Warehouse, Product,
                            RFQ ──▶ SupplierQuote   StockBatch, StockSerial
                              award ──▶ creates PO

DMS:  Folder ─▶ Document ─▶ DocumentVersion ─▶ DocumentChunk (vector embedding)
                  │                              ▲
                  ├─ FolderPermission             │
                  ├─ ScanResult                   │ used by /api/dms/qa
                  ├─ DocumentLock                 │ + /api/dms/search/semantic
                  ├─ DocumentWorkflow + Steps
                  ├─ DocumentAnnotation
                  ├─ EntityLink (polymorphic to Company/Lead/etc)
                  └─ DocumentShareLink (token + expiry)

Cross-cutting (lives outside per-app FK trees):
  AuditEntry          — every sensitive write lands here
  Notification        — in-app inbox + email + (optional) SMS
  Comment             — polymorphic via target_type + target_id
  Attachment          — polymorphic
  TagLink             — polymorphic (entity_type, entity_id)
  ApprovalRequest     — generic approval inbox
  Webhook + Delivery  — external integrations
  ApiKey              — programmatic access
  AutomationRule + Run — IFTTT engine
  PortalToken         — customer-portal magic links
  Shipment            — ties (carrier, tracking) to SO/Invoice
  CostCenter, ProfitCenter — optional dimensions on JournalLine
  FieldMask (#77)     — codename → list of masked fields per entity_type
```

**Polymorphic links use string entity_type + UUID entity_id** rather than
SQLAlchemy polymorphic inheritance. Trade-off: no FK integrity, but no
giant join trees and easy to extend (drop in a new entity type without
touching the schema). EntityLink, TagLink, Comment, Attachment, AuditEntry
all use this pattern.

**Workspace_id is NULL-safe.** During the multi-tenancy MVP we added it as
a nullable FK on flagship tables. List queries use
`(workspace_id = active OR workspace_id IS NULL)` for legacy safety. After
backfill nothing's NULL, but the OR keeps the rollout incremental — adding
the column to a new table doesn't immediately filter old data out.

---

## Cross-cutting concerns

These are the systems that cut across every router. Each has a single
entry-point function so router code stays clean.

### Authentication

* `services/auth.py` — bcrypt + python-jose JWT.
* `dependencies.py::get_current_user` — FastAPI dep that decodes the bearer
  token and loads the User. Used as a router-level dep on most files.
* SSO (#48) lives at `routers/sso.py`. Issues the same JWT after OIDC
  callback so downstream code is identical regardless of how the user
  authenticated. Uses signed (HMAC-SHA256, 10-min TTL) state token — no
  server-side state.
* Customer portal (#74) issues a *different* JWT with `kind="portal"` claim
  — narrowly scoped to one company. Rejected by `get_current_user` (uses
  bare `sub`); accepted only by the portal's own dep.
* 2FA (#45) — `users.totp_secret` + `is_totp_enabled`. Login returns
  `detail: "TOTP_REQUIRED"` when 2FA is on but no `totp_code` provided;
  the LoginPage transparently shows the code field and re-submits.

### Authorization

Three concentric layers, in order of evaluation:

```
  Codename grant (group + direct)  ─────▶  has_permission(codename)
            │
            ▼
  Project membership (when codename starts with `projects.`)  ──▶ has_permission(codename, project_id)
            │
            ▼
  Workspace scope (X-Workspace-Id header)  ──▶ get_active_workspace_id()
            │
            ▼
  Field masks (per-entity_type, per-codename)  ──▶ get_field_mask() + apply_field_mask()
```

* `acl/catalog.py` is the single source of truth for codenames. ~80 entries
  spanning `projects.*` / `sales.*` / `finance.*` / `documents.*` /
  `admin.*` / `inventory.*` / `hr.*` / `acl.*`.
* `acl/seed.py` is **idempotent + advisory-locked**. Runs at startup,
  upserts permissions, refreshes 7 system groups, seeds 4 default field
  masks.
* `acl/resolver.py::require_permission(codename)` is the FastAPI
  dependency factory. Per-request memoisation prevents repeated DB lookups.
* Field masks (#77): a row says "users WITHOUT codename `unmask_codename`
  cannot see fields X on entity_type Y". Admin always bypasses. Stored as
  `acl_field_masks(unmask_codename, entity_type, fields[])`. Applied at
  serialiser level — masked fields become `null` in the JSON response.

### Audit + automation

* `services/audit.py::log_audit(db, user, domain, action, entity_type,
  entity_id, before, after)` writes an `AuditEntry`. Swallows exceptions
  (audit must never fail the parent request).
* **Same call also fires automation events.** After writing the audit row,
  `log_audit` calls `services/automation.fire_event()` with a synthesised
  event name `f"{entity_type}.{action}"` — every audited mutation can drive
  an IFTTT rule for free.
* Automation rules support 9 condition operators (`==`, `!=`, `>`, `>=`,
  `<`, `<=`, `contains`, `in`, `exists`) on dotted-path payload fields.
  Action runners: `notify_user`, `add_tag`, `post_webhook`, `log`. Each
  evaluation writes an `AutomationRuleRun` row for transparency.

### Multi-tenancy (#46 MVP)

* `services/workspaces.py::get_active_workspace_id(request, user, db)` is
  the single resolver. Order: `X-Workspace-Id` header (membership-checked,
  admin bypass) → user's first membership → fallback to "Default"
  workspace.
* Currently applied to `Project`, `Company`, `Vendor` (flagship subset).
  Helper, header injection, switcher, seed, and backfill are all in place
  — per-entity rollout to remaining tables is mechanical follow-up.
* Frontend: `apiSlice.prepareHeaders` injects `X-Workspace-Id` from
  `localStorage`. User-menu Workspace dropdown switches; selecting calls
  `apiSlice.util.resetApiState()` so every cached list refetches under the
  new scope.

### Audit + automation hook diagram

```
  Router handler              services/audit.py            services/automation.py
  ─────────────────           ─────────────────             ──────────────────
  await db.commit()
  await log_audit(...)  ─────▶ AuditEntry inserted          
                                  │                          
                                  ▼                          
                              fire_event(event=             
                                "{entity_type}.{action}",  
                                payload={before, after})  ─▶ load active rules
                                                              for that event
                                                              │
                                                              ▼
                                                            evaluate conditions
                                                              │
                                                              ▼
                                                            run action chain
                                                            (notify / add_tag /
                                                             post_webhook / log)
                                                              │
                                                              ▼
                                                            AutomationRuleRun
                                                            (log of evaluation)
```

---

## Request lifecycle

A typical write request walks this path:

1. **Browser** issues `POST /api/crm/companies` with bearer token + `X-Workspace-Id`
   header.
2. **nginx** rate-limits (30 r/s general, 5 r/s on `/api/auth/`),
   load-balances least-conn across backend replicas, gzips, sets immutable
   cache headers on `/assets/*`.
3. **Backend** decodes JWT in `get_current_user`, attaches `User` to
   request.
4. **Router dependency** `require_permission("sales.company.manage")`
   resolves the user's effective codename set (per-request memoised).
   403s if missing.
5. **Workspace resolver** `get_active_workspace_id(request, user, db)`
   reads the header, validates membership (admin bypasses), falls back to
   user's first workspace then to Default.
6. **Field-mask resolver** (where applicable) returns the set of fields
   this user can't see for the entity type — caller `apply_field_mask()`s
   the response dict.
7. **Handler** does its work, commits.
8. **`log_audit()`** writes an AuditEntry **and** fires an automation
   event. Matching rules execute in-band (notifications written, webhooks
   queued, tags attached, etc).
9. Response shaped, returned. nginx adds `Cache-Control` headers if
   applicable.

---

## Background jobs

Two queues, dedicated workers:

| Queue | Worker | Use cases |
|---|---|---|
| `default` | `celery-worker` ×2 | Email send, SMS send (when `SMS_ENABLED=1`), CSV import, audit-driven notifications, cache warmups |
| `reports` | `celery-reports` ×1 | Monte Carlo, PDF generation, AI plan generation (#52), nightly retention scan, expiry reminders, scheduled report runs, depreciation batches |

`celery-beat` schedules:

| When | Task |
|---|---|
| 02:00 UTC nightly | `run_retention_task` — applies retention policies to docs |
| 01:00 UTC nightly | `run_expiry_reminders_task` — notifies on expiring docs |

**Result polling.** Tasks return JSON; the frontend polls
`/api/celery-tasks/{task_id}` every ~1.5s until SUCCESS / FAILURE. Used by
Monte Carlo, AI plan generation.

---

## Real-time + presence

* `websockets/manager.py::ConnectionManager` — per-project rooms. Backend
  publishes broadcasts to `redis-ws`; every replica's subscriber loops and
  fans out to its local socket connections. **Means scale-out works**:
  user A on backend-1 changes a task, user B on backend-2 sees it
  instantly.
* `usePresence` (frontend) + `/api/presence/*` (backend, Redis-backed)
  drives the avatar stack — "who else is on this page".
* WebSocket URL `/ws/{project_id}`. Auth via JWT in the query string at
  upgrade time (browsers can't send custom headers on WS).

---

## Extension points

The system has been built so that integrations are pluggable, with a
**graceful fallback when not configured** so demos work without external
API keys.

| Subsystem | Adapter location | Configured via | Fallback |
|---|---|---|---|
| File storage | `services/storage.py` (`LocalStorage`, `S3Storage`) | `DMS_STORAGE` + S3 vars | local dir |
| Email | `services/email.py` (SMTP) | `SMTP_HOST` etc | logs the message |
| SMS | `services/sms.py` (Twilio REST via `urllib`) | `SMS_ENABLED` + `TWILIO_*` | logs the message |
| Payments | `services/stripe_client.py` (REST via httpx) | `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` | endpoints return 503 |
| LLM | `services/llm.py` (OpenAI-compatible) | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | deterministic mock plan |
| Embeddings | `services/embeddings.py` (OpenAI-compatible) | same `LLM_*` vars | hashed token-frequency vector |
| SSO | `routers/sso.py` (OIDC) | per-provider row in `sso_providers` | login page hides SSO buttons |
| Shipping | `routers/shipping.py::CarrierAdapter` | per-carrier subclass | manual no-op adapter |
| OCR | tesseract via `pytesseract` | `DMS_OCR_ENABLED=1` | unset, no extraction |

**Webhook security** — Stripe verifies `Stripe-Signature` (HMAC-SHA256,
5-min replay window, stdlib only). Generic shipping webhook trusts source
(production should add HMAC or IP allowlist).

---

## Observability + ops

* **`/metrics`** — Prometheus instrumentation via
  `prometheus-fastapi-instrumentator`. Per-handler latency histograms,
  request counters. Excludes `/api/health` from labels to avoid cardinality
  blowup.
* **Grafana** at `:3001` — provisioned datasource pointed at Prometheus,
  pre-built backend dashboard.
* **Audit log** at `/admin/activity` — filterable by domain, surfaces
  every sensitive mutation across the stack.
* **Automation runs** at `/admin/automation` — recent rule evaluations
  with status (success / partial / failed / skipped) and per-action errors.
* **Celery results** are stored in Redis (broker DB 1).

**Schema migrations** are deliberately Alembic-free for now. The runner is
`services/migrations.py`:

* Holds a dict of `{label: SQL}` of `ALTER TABLE ... ADD COLUMN IF NOT
  EXISTS` and `CREATE INDEX IF NOT EXISTS` statements.
* Each statement runs in **its own transaction** so one failure doesn't
  poison the rest (Postgres aborts the whole txn on any DDL error).
* The whole pass is wrapped in a `pg_advisory_lock(73126903)` so the two
  backend replicas don't race each other on `CREATE INDEX IF NOT EXISTS`
  (which can hit `pg_class_relname_nsp_index` unique-violations between
  the existence check and the catalog insert).

**Why no Alembic.** The model surface evolves fast and most changes are
additive (new tables, new columns, new indexes). `create_all` + the
additive runner cover 99% of cases. When we need a destructive migration
(rename a column, change a type) we'll add Alembic; until then the runner
is enough and ships zero tooling overhead.

---

## Where to start when adding things

| You want to add... | Start here |
|---|---|
| A new table | `backend/app/models/<domain>.py` → register in `models/__init__.py`. Boot will `create_all()`. For altering an existing table, add to `services/migrations.py`. |
| A new endpoint | `backend/app/routers/<domain>.py` → add to `app.include_router(...)` in `main.py`. |
| A new permission | `backend/app/acl/catalog.py` → reseeded at next boot. Reference via `Depends(require_permission("..."))`. |
| A new automation event | Just call `await fire_event(db, "your.event", payload)` from the router. Add to `SUPPORTED_EVENTS` in `services/automation.py` so the rule-builder UI shows it. |
| A new Celery task | `backend/app/tasks.py` (default queue) or add `queue="reports"` for heavy work. Submit with `.delay(...)`, poll via `/api/celery-tasks/{id}`. |
| A new list page | `frontend/src/pages/<app>/<Name>Page.tsx`. Use `<DataTable columns={...} data={...} onRowClick={(r) => openPeek("entity", r.id)} />`. Wire route in `App.tsx`, nav in `shell/navConfig.ts`. |
| A new drawer body | `frontend/src/shell/drawerBodyRegistrations.tsx` — add a `registerDrawerBody("entity", { title, tabs })` call. The drawer mounts globally. |
| A new RTK Query endpoint | `frontend/src/services/api.ts` — add to `endpoints` + the auto-generated hook is exported. Use a tag for invalidation. |
| A new locale string | `frontend/src/i18n/en.json` — reference via `t("path.to.string")`. |
| A new entity drawer | Use the `OverviewGrid` + `CommentsTab` helpers from `shell/drawerTabs.tsx`. Currency/dates via `useFormat()`. |
| Make something workspace-scoped | Add `workspace_id` column (additive migration), call `get_active_workspace_id()` in the list/create endpoints. |
| Mask a sensitive field | Add a row to `acl_field_masks` (or seed it in `acl/seed.py`'s `DEFAULT_FIELD_MASKS`). Use `apply_field_mask(get_field_mask(db, user, "entity_type"))` in the response shaper. |
| A new keyboard shortcut | `useHotkeys([{ combo: "ctrl+shift+x", handler: ... }])` in any component, or add to `ShortcutsCheatsheet.tsx` for global ones. |

---

## Files of note that don't fit elsewhere

* `seed_fake_data.py` — populates 77 tables with realistic demo data
  (3 small + 3 large project templates + 28 enterprise companies + 25
  vendors + DMS content + ledger + admin cross-cutting). Idempotent on
  re-run for the wider section.
* `tests/conftest.py` — overrides `get_db` and `get_current_user` so tests
  run against an in-memory sqlite with an admin test user. Seeds the
  permission catalog per test so `require_permission()` succeeds.
* `pgbouncer/pgbouncer.ini` — transaction pool config. Tune
  `default_pool_size` based on Postgres `max_connections`.
* `nginx/nginx.conf` — rate limits, gzip, WebSocket upgrade, immutable
  asset caching. The `least_conn` upstream is what enables horizontal
  backend scale.
* `tasks.md` — the historical backlog. Reads as a changelog now that
  almost everything's shipped.
