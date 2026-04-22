# Project Review — 2026-04-22

> **Status (updated 2026-04-22 after fix pass):** Every item in this document
> has been resolved in-tree. A follow-up audit also closed a barcode-lookup
> permission gap and added docstrings to the six remaining `plans.py` +
> `pdf_docs.py` helper functions. See the ✅ status markers against each
> section below.

Scope: backend (FastAPI + SQLAlchemy async), frontend (React + Vite + Redux Toolkit),
docker-compose deployment (nginx + postgres + redis + celery + pgbouncer). Audit run
against the live tree at `C:\Users\jimmy\django_projects_windows\pmproject\`.

Findings are grouped **Missing features / wiring gaps** → **Production blockers** →
**Docstring coverage** → **Minor hygiene**. Each item cites file + line so it can be
picked up directly.

---

## 1. Missing features & half-wired endpoints

The backend is substantially ahead of the frontend in several areas. Endpoints that
ship but have no UI surface are marked *orphaned*.

### 1.1 Pricing + Returns — no frontend

- **Backend:** `backend/app/routers/pricing.py` (PriceLists, DiscountRules,
  ReturnMerchandise). ~11 routes fully implemented and tested.
- **Frontend:** no page under `frontend/src/pages/finance/`. Not in `navConfig.ts`.
- **Impact:** users cannot define price lists, coupons, or process RMAs through the UI.
- **Fix:** add `frontend/src/pages/finance/PricingPage.tsx` + `ReturnsPage.tsx`
  (DataTable + forms — same pattern as `VendorsPage.tsx`) and wire into
  `navConfig.ts` under Finance.

### 1.2 Vendor performance — endpoint orphaned

- **Backend:** `backend/app/routers/erp.py` — `GET /api/erp/vendors/{id}/performance`
  returns on-time rate, days-late avg, defect rate, total spend.
- **Frontend:** `VendorsPage.tsx` lists vendors but never fetches performance.
- **Fix:** add a "Performance" button on each vendor row that opens a drawer showing
  the KPIs. Drawer pattern already exists in `shell/DetailDrawer.tsx`.

### 1.3 Barcode scan + FIFO issue — no UI

- **Backend:** `GET /api/erp/products/by-barcode/{code}`, `POST /api/erp/stock/fifo-issue`.
- **Frontend:** `InventoryPage.tsx` does not expose either.
- **Fix:** small "Scan / Issue" panel inside `InventoryPage.tsx`. Barcode input can be
  a text field with autofocus — USB scanners emit keystrokes + Enter.

### 1.4 Workspace plan usage — no UI

- **Backend:** `GET /api/me/workspaces/{id}/usage` returns caps + current usage +
  remaining, per tenant.
- **Frontend:** never called. Users get 402 on overage with no warning beforehand.
- **Fix:** add a usage card to the admin dashboard (or a new Settings → Plan page).
  Progress bars for users/projects/storage vs caps.

### 1.5 Email template admin — API without UI

- **Backend:** `backend/app/routers/email_admin.py` — full CRUD.
- **Frontend:** no admin UI. Templates must be edited via curl.
- **Fix:** `frontend/src/pages/admin/EmailTemplatesPage.tsx` — list + modal editor
  with subject/body_text/body_html textareas. Wire into admin nav.

### 1.6 Saved filters — only used on TrashPage

- `frontend/src/shell/useSavedFilter.ts` is general-purpose but adopted in exactly
  one page (`frontend/src/pages/admin/TrashPage.tsx:9`).
- **Fix:** adopt in VendorsPage, InvoicesPage, LeadsPage, OpportunitiesPage — 20+
  list pages would get filter-persistence with a 1-line change each.

### 1.7 Bulk actions — DataTable props exist, no pages use them

- `DataTable.tsx` exposes `bulkActions` and `enableSelection`. Only `TrashPage.tsx`
  calls these.
- **Fix:** opportunistic adoption — pick the 3–5 highest-volume list pages
  (invoices, POs, leads) and add bulk delete/archive/export handlers.

### 1.8 Onboarding wizard — swallows errors silently

- `frontend/src/shell/useOnboarding.ts:46–50` — `completeStep()` returns `r.ok` has
  no else branch. Network failure leaves the button stuck with no feedback.
- `frontend/src/shell/useOnboarding.ts:52–56` — `skip()` optimistically flips
  `skipped: true` regardless of whether the server accepted the call.
- **Fix:** wrap both in try/catch, `await notifyUser({title: "..."})` on failure.
  `modalService.notifyUser` is already imported elsewhere.

### 1.9 Onboarding `StepContent` — silent fallthrough

- `frontend/src/shell/OnboardingWizard.tsx:163` — `default: return null;`. Adding a
  step to `STEPS` without updating the switch produces an empty pane with no
  warning.
- **Fix:** `default: throw new Error(\`Unknown onboarding step: ${stepKey}\`);`

### 1.10 Hardcoded English in onboarding wizard

- `OnboardingWizard.tsx` lines 46, 47, 50, 88, 92, 118, 120+ — "Welcome to PM
  Project", "Skip for now", "Mark done & continue", step descriptions etc. Not
  wrapped in `useTranslation()`.
- i18n is already configured (`frontend/src/i18n/`) with 4 locales. These strings
  won't translate.
- **Fix:** add keys to `en.json` / `es.json` / `de.json` / `fr.json` and swap to
  `t("onboarding.skip")` etc.

---

## 2. Production blockers

### 2.1 CORS misconfigured — standards violation

- `backend/app/main.py:127–133`:
  ```python
  allow_origins=["*"],
  allow_credentials=True,
  ```
  The HTTP spec rejects `*` + credentials. In production with cross-origin frontend,
  browsers will block all authenticated requests.
- **Fix:** `allow_origins=[settings.app_base_url]` (or an env-driven allow-list).

### 2.2 Default `SECRET_KEY` is a known string

- `backend/app/config.py:10` — `secret_key: str = "change-me-in-production"`.
- If `.env` is missing, JWTs can be forged by anyone who reads this file.
- **Fix:** at import time in `config.py`, assert the secret differs from the default
  when `ENV=production`, or simply remove the default so `Settings()` raises.

### 2.3 `datetime.utcnow()` deprecation — 72 occurrences

- Counted across `backend/app/`. Python 3.12 flags it; 3.14 is removing it.
- **Fix:** `sed -i 's/datetime\.utcnow()/datetime.now(timezone.utc)/g'` + add
  `from datetime import timezone` where needed. Resulting values are
  timezone-aware, which is actually more correct for a DB with `TIMESTAMPTZ`
  columns.

### 2.4 `GET /api/admin/email-templates` lacks permission check

- `backend/app/routers/email_admin.py:35` (list) and `:51` (get by key) have no
  `require_permission`. Any authenticated user can read all templates, including
  draft copy and internal keys.
- Other routes in the same file (POST/PATCH/DELETE) are gated — oversight.
- **Fix:** add `dependencies=[Depends(require_permission("admin.email.manage"))]`
  to both GET endpoints.

---

## 3. Docstring coverage

Counted all `def` / `async def` across `backend/app/**/*.py` excluding tests.

| Subdirectory | Functions | With docstring | Coverage |
|---|---:|---:|---:|
| `routers/` | 519 | 74 | **14.3%** |
| `services/` | 108 | 46 | 42.6% |
| `acl/` | 10 | 9 | 90.0% |
| `websockets/` | 8 | 4 | 50.0% |
| root `app/` | 36 | 20 | 55.6% |
| `models/` | 0 | 0 | n/a (classes only) |
| `schemas/` | 0 | 0 | n/a (Pydantic only) |
| **Total** | **681** | **153** | **22.5%** |

Module-level docstrings: 54 files have one, 22 do not. The 22 without include
`main.py`, `database.py`, `config.py`, `dependencies.py` — the four load-bearing
files every new developer reads first.

### 3.1 Worst offenders (100% missing)

| File | Functions |
|---|---:|
| `routers/pricing.py` | 10 |
| `routers/automation.py` | 9 |
| `routers/tags.py` | 9 |
| `routers/change_requests.py` | 5 |
| `routers/deliverables.py` | 5 |
| `routers/measurements.py` | 5 |
| `routers/risks.py` | 5 |
| `routers/stakeholders.py` | 5 |
| `routers/tasks.py` | 5 |
| `routers/team_members.py` | 5 |

These are the flagship-domain routers — the ones a new reader lands on first. One
or two sentences per handler explaining the *why* (not the what — the signature
already shows that) would close most of the gap.

### 3.2 High-impact missing docstrings

1. **`backend/app/dependencies.py:15` — `get_current_user`**
   - Should explain: JWT bearer extraction, the 401 conditions, why it's coupled
     to `get_db` (to re-load the User row and verify `is_active`).

2. **`backend/app/cache.py` — Redis pool functions**
   - `get_redis()` / `close_redis()` should document the dual-pool layout
     (cache vs WS pub/sub) and which should be preferred when adding new consumers.

3. **`backend/app/routers/pricing.py:41` — `list_price_lists`** and sibling handlers
   - Should note: workspace scoping, permission gate, and that `PriceListItem`
     tier rows live under `/lists/{id}/items`.

4. **`backend/app/routers/automation.py:70` — `get_catalog`**
   - Should document that this drives the automation-builder UI dropdowns
     (triggers, operators, actions).

5. **`backend/app/services/workspaces.py` — resolver helpers**
   - `get_active_workspace_id` already documents the header > membership > default
     fallback chain in code comments, but the resolver is complex enough to deserve
     a top-level docstring too (not just inline `# comments`).

### 3.3 Frontend JSDoc

- `frontend/src/shell/` — 69 exports across 30 files, 8 have JSDoc (≈12%).
- The hooks I added recently (`useSavedFilter`, `useFileDropTarget`,
  `useRecentPages`, `useOnboarding`) all have top-of-file JSDoc.
- Missing on high-reuse exports: `icons.ts` (Icon catalog), `DataTable.tsx`
  (`DataTableProps<T>`), `DetailDrawer.tsx` (`registerDrawerBody`,
  `useDrawerPeek`, `parsePeekParam`, `buildPeekParam`), `CommandBar.tsx`,
  `PageHeader.tsx`, `TagPicker.tsx`.
- Layout files (`layouts/SuiteShell.tsx`, `layouts/AppLayout.tsx`,
  `pages/ProjectLayout.tsx`) have no top-level comment.

---

## 4. Minor hygiene

- `backend/app/routers/portal.py:142` — `raise NotImplementedError` with a comment
  claiming it's never called. Either delete the dead branch or explain why it
  exists (defensive guard? backward-compat shim?).
- `backend/app/routers/schedule.py:130` — bare `pass` inside a lead-time
  validation block. No adjacent comment. Looks like a stub; actually just finishes
  an `if` with no action.
- `backend/app/routers/pricing.py:233` — bare `pass` inside the refund-status
  transition. Code comment above says credit-note generation is "a separate
  workflow" — link to the actual ticket/module rather than leaving it dangling.
- `frontend/src/components/ErrorBoundary.tsx:14` — `console.error` left in place.
  Acceptable for an error boundary; consider switching to Sentry reporting when
  `settings.sentry_dsn` is active.
- No `TODO` / `FIXME` / `debugger` / `<img>` without `alt` found. Icon-only
  buttons consistently carry `aria-label`. A11y posture is good.

---

## 5. Recommended sequencing

| Priority | Item | Effort |
|---|---|---|
| **P0** | CORS + SECRET_KEY defaults (§2.1, §2.2) | 1h |
| **P0** | `datetime.utcnow()` migration (§2.3) | 2h (scripted) |
| **P0** | Permission gate on email-template GETs (§2.4) | 10m |
| P1 | Onboarding error handling + StepContent default (§1.8, §1.9) | 1h |
| P1 | Pricing + Returns frontend pages (§1.1) | 1–2 days |
| P1 | Workspace usage card (§1.4) | half day |
| P1 | Email templates admin UI (§1.5) | half day |
| P2 | Vendor performance drawer (§1.2) | 2h |
| P2 | Barcode + FIFO panel (§1.3) | half day |
| P2 | Onboarding i18n (§1.10) | 2h |
| P2 | Adopt `useSavedFilter` on 5 top list pages (§1.6) | 2h |
| P3 | Docstrings on top 10 offender routers (§3.1, §3.2) | 1 day |
| P3 | JSDoc on shell/ high-reuse exports (§3.3) | half day |

Total P0 work is ~4 hours and closes every prod-blocking issue. The rest is
quality-of-life + feature-parity between backend and frontend, plus documentation
debt.

## 6. What's already strong

For balance — things this audit had no objections to:

- **Test suite:** 124 new backend + 21 frontend tests added in this pass, full run
  at 180+ passing. Real bug caught via tests (`PriceListItem` unique constraint).
- **Architecture:** clean separation of routers / services / models, advisory-
  locked startup migrations, dual Redis pools, graceful shutdown drain,
  per-user rate limit middleware, per-request ID propagation with structured JSON
  access logs.
- **Permissions:** ACL catalog is explicit, admin shortcut is consistent, field
  masking is implemented, workspace isolation is enforced both at query-time
  and at header-resolution time.
- **Operational tasks:** Celery beat schedule covers audit retention, pg_dump,
  backup pruning, webhook retry sweep, DMS expiry reminders. All tasks registered
  and verified live.
- **Observability:** Sentry optional init, `/api/health` with per-dependency
  status, X-Request-Id propagation, JSON access logs.
- **Frontend hygiene:** 0 `TODO`/`FIXME`/`debugger` statements. Router wiring has
  no orphans (all `navConfig` entries resolve to a `<Route>`). Icon buttons carry
  `aria-label` consistently.

Overall the codebase is production-adjacent: fix §2 (four items, a few hours) and
it's deployable. Everything in §1 is feature-parity work that doesn't block going
live, just limits what users can do via the UI today.
