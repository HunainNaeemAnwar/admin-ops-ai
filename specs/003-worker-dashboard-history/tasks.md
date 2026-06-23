---

description: "Task list for Worker Dashboard + History Auto-Archive feature implementation"
---

# Tasks: Worker Dashboard + History Auto-Archive

**Input**: Design documents from `specs/003-worker-dashboard-history/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/endpoints.md

**Tests**: No automated tests requested in spec — manual browser testing per spec acceptance criteria

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

## Path Conventions

- Single project at repository root
- Existing files modified: `web_ui/routes.py`, `web_ui/templates/index.html`, `tools/database.py`, `tools/export_tools.py`, `config.py`
- New files created: `web_ui/templates/worker_dashboard.html`

---

## Phase 1: Setup

**Purpose**: Project initialization — config paths, directories, and infrastructure

- [ ] T001 [P] Add `HISTORY_DIR` path to `config.py` (default: `DATA_DIR / "history"`) and ensure directory is created in startup mkdir loop

**Checkpoint**: Setup complete — history directory exists, config has new path

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 Create `worker_monthly_history` table in `tools/database.py` — add CREATE TABLE statement to `init_db()` with all fields: `(id, worker_id, year, month, product_id, total_quantity, gross_amount, archived_at)`, foreign keys, UNIQUE constraint, and index `idx_history_worker_month`
- [ ] T003 [P] Implement `get_worker_daily_breakdown(worker_id, year, month)` in `tools/database.py` — query daily_log + products for current month, return list of dicts with `{date, status, products: {code: qty}}` format per spec contract. For absent days: single entry with `status="absent"`. For no-data days: entry with all zeros.
- [ ] T004 [P] Implement `is_month_archived(year, month)` in `tools/database.py` — SELECT COUNT from `worker_monthly_history`, return bool
- [ ] T005 [P] Implement `insert_worker_history(worker_id, year, month, product_id, total_quantity, gross_amount)` in `tools/database.py` — INSERT OR IGNORE to handle idempotency
- [ ] T006 [P] Implement `get_worker_history_month(worker_id, year, month)` in `tools/database.py` — query aggregated totals from `worker_monthly_history` for a worker+month

**Checkpoint**: Foundation ready — all DB functions exist and are testable via python shell

---

## Phase 3: User Stories 1, 2, 3 — Worker Dashboard + Excel + Admin Route (Priority: P1) 🎯 MVP

**Goal**: Public worker dashboard at `/` with monthly calendar table, worker/month dropdowns, individual Excel download. Father dashboard moves to `/admin` with OAuth.

**Independent Test (US1)**: Open `/`, select a worker — monthly table shows correct dates, quantities, absent markings
**Independent Test (US2)**: Select worker+month, click "Download Excel" — .xlsx file downloads with correct data
**Independent Test (US3)**: Visit `/admin` without login — see Google sign-in. Login as father — all management features accessible.

### Implementation for User Stories 1, 2, 3

**US1 + US2 share the same dashboard template and API routes. US3 is a route restructure of existing code.**

- [ ] T007 [P] [US1] Create `web_ui/templates/worker_dashboard.html` — monthly calendar table template with:
  - Worker selection dropdown (populated from workers list)
  - Month/year selection dropdown
  - Table with dates (1-end) as rows, products as columns
  - Total row and total column
  - Absent days shown as "ABSENT" spanning all product columns
  - "Download Excel" button (links to `/api/worker/{name}/excel/{year}/{month}`)
  - Clean, mobile-friendly CSS (similar styling to existing index.html)
  - No auth/login controls — fully public

- [ ] T008 [P] [US1] Implement `GET /` route in `web_ui/routes.py` — render `worker_dashboard.html` with workers list, products list, current month/year. No auth required. Include archive check trigger on page load.

- [ ] T009 [P] [US1] Implement `GET /api/workers` route in `web_ui/routes.py` — return JSON list of all workers. No auth. Uses existing `get_all_workers()`.

- [ ] T010 [P] [US1] Implement `GET /api/products` route in `web_ui/routes.py` — return JSON list of all products. No auth. Uses existing `get_all_products()`.

- [ ] T011 [P] [US1] Implement `GET /api/worker/{name}/month/{year}/{month}` route in `web_ui/routes.py` — return JSON with daily breakdown. For current month: use `get_worker_daily_breakdown()`. For archived months: use `get_worker_history_month()` + reconstruct daily format. No auth.

- [ ] T012 [P] [US2] Implement `generate_worker_excel(worker_name, year, month)` in `tools/export_tools.py` — generates Excel with: dates as rows, products as columns, quantities in cells, totals row, absent days marked. Returns file path. Uses existing `_style_header()` and `_thin_border()` helpers.

- [ ] T013 [P] [US2] Implement `GET /api/worker/{name}/excel/{year}/{month}` route in `web_ui/routes.py` — call `generate_worker_excel()`, return file as download response with correct Content-Disposition header. No auth.

- [ ] T014 [US3] Restructure existing routes in `web_ui/routes.py` — move all current management routes under `/admin/` prefix:
  - `GET /` → move to `GET /admin` (father dashboard)
  - `GET /login` → move to `GET /admin/login`
  - `GET /oauth/callback` → keep at `GET /oauth/callback` (OAuth callback URL is fixed in Google Console)
  - `GET /logout` → move to `GET /admin/logout`
  - `POST /record` → move to `POST /admin/record`
  - `POST /record-text` → move to `POST /admin/record-text`
  - `POST /rejection` → move to `POST /admin/rejection`
  - `POST /advance` → move to `POST /admin/advance`
  - `POST /payslip` → move to `POST /admin/payslip`
  - `POST /email` → move to `POST /admin/email`
  - `POST /chat` → move to `POST /admin/chat`
  - `GET /daily` → move to `GET /admin/daily`
  - `GET /monthly` → move to `GET /admin/monthly`
  - `GET /workers` → move to `GET /admin/workers`
  - `GET /worker/{name}` → move to `GET /admin/worker/{name}`
  - `GET /products` → move to `GET /admin/products`
  - `PUT /products/{code}` → move to `PUT /admin/products/{code}`

- [ ] T015 [US3] Verify father's `index.html` template works correctly at `/admin` — update template references if needed (relative paths, links to management features)

**Checkpoint**: At this point, US1, US2, and US3 should all be fully functional and independently testable

---

## Phase 4: User Story 4 — Monthly Data Auto-Archive (Priority: P2)

**Goal**: On the 1st day of a new month, previous month's data is automatically archived to history table + Excel files.

**Independent Test**: Set date to 1st of new month, visit dashboard — verify previous month archived in DB + Excel files in `data/history/`

### Implementation for User Story 4

- [ ] T016 [P] [US4] Implement `archive_previous_month()` function in `tools/database.py` (or a new `tools/archive_tools.py`):
  1. Determine previous month (year, month) based on current date
  2. Check `is_month_archived()` — skip if already archived
  3. For each active worker × product: aggregate `SUM(daily_log.quantity)` for previous month
  4. Calculate `gross_amount = total_quantity × product.rate`
  5. INSERT into `worker_monthly_history` using `insert_worker_history()`
  6. Call `generate_worker_excel()` for each worker to save Excel to `data/history/`
  7. Return summary string of what was archived

- [ ] T017 [US4] Integrate archive trigger into `GET /` route in `web_ui/routes.py` — on every dashboard load, check if today is 1st of month AND previous month not archived. If yes, run `archive_previous_month()`. This runs silently in the background before page render.

**Checkpoint**: Auto-archive works — previous month gets archived on first visit of new month

---

## Phase 5: User Story 5 — Worker Views Historical Months (Priority: P3)

**Goal**: Archived months are viewable through the dashboard month selector. Data loads from history table.

**Independent Test**: Archive a month, then select it from dropdown — verify table shows correct aggregated data

### Implementation for User Story 5

- [ ] T018 [US5] Update `GET /api/worker/{name}/month/{year}/{month}` in `web_ui/routes.py` — add logic:
  - If (year, month) is current month → query `get_worker_daily_breakdown()` from `daily_log` (live data)
  - If (year, month) is archived → query `get_worker_history_month()` from `worker_monthly_history` (aggregated data)
  - If no data at all → return empty days array with info message
  - Add `"source": "live" | "archived" | "none"` field in response JSON

- [ ] T019 [US5] Update `web_ui/templates/worker_dashboard.html` — add visual indicator showing whether data is "Live (Current Month)" or "Archived (Previous Month)" in the table header

**Checkpoint**: Historical months fully viewable through dropdown with clear source indicators

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, edge case handling, and documentation

- [ ] T020 [P] Handle edge cases in `web_ui/routes.py`:
  - Invalid worker name → 404 JSON response with "Worker not found"
  - Invalid month ( >12 or <1 ) → 400 JSON response
  - Future month with no data → empty table with "No production data for this month"
  - Worker with zero data for selected month → empty table with all zeros
  - Archive already exists → idempotent (no duplicate)

- [ ] T021 [P] Update `worker_dashboard.html` for mobile responsiveness — ensure calendar table is scrollable horizontally on small screens (CSS `overflow-x: auto` on table container)

- [ ] T022 [P] Add archive indicator badge on `worker_dashboard.html` — show small "Archived" tag next to month name in dropdown for months that have data in history table (call `/api/history/check` or embed in page data)

- [ ] T023 Run full manual verification:
  1. Open `/` — worker dashboard loads with current month
  2. Select different workers — table updates
  3. Select different months — table updates
  4. Click "Download Excel" — file downloads with correct data
  5. Visit `/admin` — OAuth login required
  6. Login as father — all management features accessible
  7. (If on 1st of month) Verify auto-archive runs
  8. Select archived month — data shows from history

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1+US2+US3 (Phase 3)**: Depends on Foundational — all P1 stories can proceed in parallel
- **US4 (Phase 4)**: Depends on Foundational + US2 (needs `generate_worker_excel()`) + US1 (needs dashboard route for trigger)
- **US5 (Phase 5)**: Depends on US4 (needs archived data to view)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (Phase 2) — needs `get_worker_daily_breakdown()`
- **US2 (P1)**: Depends on Foundational (Phase 2) — needs DB functions for data
- **US3 (P1)**: Depends on Foundational (Phase 2) — no code dependency on US1/US2 (independent route restructure)
- **US4 (P2)**: Depends on Foundational + US2 (Excel export) + US1 (dashboard trigger)
- **US5 (P3)**: Depends on US4 (needs archived data)

### Within Each Phase

- Tasks marked [P] can run in parallel
- Within US1: template → route → API
- Within US2: export function → route
- Within US3: route restructure → template verify

### Parallel Opportunities

```
Phase 2: T003 + T004 + T005 + T006 can run in parallel (different functions in same file)
Phase 3: T007 + T008 + T009 + T010 + T011 + T012 + T013 can run in parallel (different files)
Phase 3: T014 (route restructure) is independent and can run alongside template work
Phase 4: T016 + T017 sequential (archive function → integration)
Phase 5: T018 + T019 sequential (API logic → template update)
Phase 6: T020 + T021 + T022 can run in parallel
```

---

## Parallel Example: Phase 3 (All P1 Stories)

```bash
# Launch US1 + US2 + US3 tasks in parallel:
Task: "T007 Create worker_dashboard.html template"
Task: "T008 Implement GET / - worker dashboard route"
Task: "T009 Implement GET /api/workers"
Task: "T010 Implement GET /api/products"
Task: "T011 Implement GET /api/worker/{name}/month/{year}/{month}"
Task: "T012 Implement generate_worker_excel in export_tools.py"
Task: "T013 Implement GET /api/worker/{name}/excel/{year}/{month}"
Task: "T014 Move all management routes to /admin/ prefix"
```

---

## Implementation Strategy

### MVP First (Phase 3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: All three P1 stories together
4. **STOP and VALIDATE**: Worker dashboard shows data, Excel downloads, admin panel at /admin works
5. Deploy/demo father and workers can use the system

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready (DB functions working)
2. + Phase 3 (US1+US2+US3) → **MVP!** Worker dashboard live, admin at /admin
3. + Phase 4 (US4) → Auto-archive works at month boundary
4. + Phase 5 (US5) → History viewing from archive
5. + Phase 6 → Polish, edge cases, mobile responsive

### Single-Developer Order

```
T001 → T002 → T003+T004+T005+T006 → T007+T014 → T008+T009+T010+T011+T012+T013
→ T015 → T016 → T017 → T018 → T019 → T020+T021+T022 → T023
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1, US2, US3 are all P1 — highest priority
- The archive trigger (US4) uses a silent check on dashboard page load — no user-visible action
- All existing management features must remain unchanged after the `/admin` route restructure
- The OAuth callback route `/oauth/callback` stays at root level — Google Console redirect URI is fixed
- No new external dependencies needed — all work uses existing libraries (FastAPI, openpyxl, sqlite3)
