---

description: "Task list for Backend Core System Phase 1 implementation"
---

# Tasks: Backend Core System — Phase 1

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22
**Input**: spec.md (5 user stories, P1-P5), plan.md, data-model.md, contracts/ (database, tools, endpoints)
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description with exact file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

## Phase 1: Setup & Environment

**Purpose**: Project initialization and dependency configuration

- [ ] T001 [P] Update `config.py` with new env vars (FATHER_EMAIL, FRONTEND_URL, GMAIL_REDIRECT_URI, RATE_NUT, RATE_10X20, RATE_6X25, RATE_6X30, RATE_10X25, FIXED_WORKERS, DATABASE_URL)
- [ ] T002 [P] Create `tests/` directory with `__init__.py` for test infrastructure
- [ ] T003 [P] Remove old `tools/excel_tools.py` and `tools/calc_tools.py` (replaced by database.py + export_tools.py + report_tools.py)

---

## Phase 2: Foundation — Database Layer (Blocks ALL User Stories)

**Purpose**: Core database infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create `tools/database.py` with SQLite connection manager (get_db(), execute(), fetch_all(), fetch_one()) and schema initialization (CREATE TABLE statements for workers, products, daily_log, rejections, advances, payslips)
- [ ] T005 Create `seed.py` to populate workers table from FIXED_WORKERS env var and products table from RATE_* env vars
- [ ] T006 Update `config.py` to initialize data directories and call database setup on import

**Checkpoint**: Database ready — tables created, workers + products seeded

---

## Phase 3: User Story 1 — Record Daily Production (Priority: P1) 🎯 MVP

**Goal**: Father can record daily production via Roman Urdu chat and get confirmation summaries

**Independent Test**: Father says "Aj Kaleem ne 300 nut aur 150 10\*20 kiye", agent confirms with breakdown

- [ ] T007 [P] [US1] Implement daily_log CRUD in `tools/database.py` (insert_log(), get_logs_for_date(), get_logs_for_worker(), update_log(), ensure_day_complete())
- [ ] T008 [P] [US1] Create `tools/production_tools.py` with log_production() and update_entry() functions (validate product codes, calculate rates, insert daily_log, auto-fill absent workers)
- [ ] T009 [P] [US1] Update `agent_system/data_extractor.py` to parse Roman Urdu for patterns like "sab k X", "X ne Y nhi bnaya", "X ki chutti thi", and dynamic multi-worker entries
- [ ] T010 [US1] Update `agent_system/orchestrator.py` — add log_production_tool, mark_absent_tool, update_entry_tool, and updated dynamic instructions for US1 scenarios

**Checkpoint**: Father can log production for any worker, agent confirms, daily totals queryable

---

## Phase 4: User Story 2 — Track Monthly Finishes (Priority: P2)

**Goal**: Father records rejections (department-level, equal distribution) and advance payments

**Independent Test**: Father says "June k mahinay main 1000 nut reject hwa" then "Kaleem k rejection mat kato" — distribution recalculates

- [ ] T011 [P] [US2] Create `tools/rejection_tools.py` with log_rejection() (INSERT into rejections table with year/month/product/total_qty) and distribute_rejection() (calculate per-worker share, exclude workers from JSON array)
- [ ] T012 [P] [US2] Create `tools/advance_tools.py` with record_advance() (INSERT into advances table with worker_id/amount/month/year) and get_advances_for_month() (SELECT sum for payslip)
- [ ] T013 [US2] Update `agent_system/orchestrator.py` — add log_rejection_tool, record_advance_tool, and instructions for rejection/advance handling

**Checkpoint**: Rejection recorded, distributed, advances tracked. Ready for payslip calculation.

---

## Phase 5: User Story 3 — Generate Monthly Payslips (Priority: P3)

**Goal**: Father generates PDF + Excel payslips with full financial breakdown

**Independent Test**: Father says "Sab ki payslip banao June 2026 ki" — PDFs and Excels generated for all workers

- [ ] T014 [P] [US3] Create `tools/report_tools.py` with get_daily_status() (aggregate daily_log by date, check absent status), get_summary() (daily/weekly/monthly aggregation with per-worker and department views)
- [ ] T015 [P] [US3] Update `tools/payslip_tools.py` — rewrite to calculate from database (read daily_log, rejections, advances, products; compute gross/rejection_deduction/advance_deduction/tax/net_payable; generate PDF via reportlab and Excel via openpyxl)
- [ ] T016 [US3] Update `agent_system/orchestrator.py` — add generate_payslip_tool, list_catalog_tool, get_daily_status_tool, get_summary_tool, and instructions for payslip generation flow

**Checkpoint**: Payslips generated with correct financial calculations, files saved to data/pay_slips/

---

## Phase 6: User Story 4 — Send Reports to Manager (Priority: P4)

**Goal**: Father triggers daily/weekly/monthly production reports to manager (quantities only)

**Independent Test**: Father says "Manager ko daily email bhejo" — manager receives email with per-product department totals

- [ ] T017 [P] [US4] Create `tools/export_tools.py` with generate_excel_report() (openpyxl workbook with department totals per product, no financial data, no worker names)
- [ ] T018 [P] [US4] Update `tools/email_tools.py` — implement send_report() that composes department-only email (plain text for daily, Excel attachment for weekly/monthly), NEVER auto-sends, returns error on failure
- [ ] T019 [US4] Update `agent_system/orchestrator.py` — add send_report_tool with instructions: "NEVER include individual data, NEVER include financials, ONLY department product totals"

**Checkpoint**: Father triggers report, manager receives it with correct quantities-only format

---

## Phase 7: User Story 5 — Access System Securely (Priority: P5)

**Goal**: Google OAuth login with FATHER_EMAIL gate — father gets full access, others read-only

**Independent Test**: Father logs in with Google → sees chat. Other user logs in → sees dashboard only

- [ ] T020 [P] [US5] Update `tools/oauth_tools.py` to add two-URI flow support (GMAIL_REDIRECT_URI for callback, FRONTEND_URL for redirect after auth), add is_father_email() check
- [ ] T021 [P] [US5] Add `get_current_user()` dependency and `require_father()` auth middleware to `web_ui/routes.py` — check OAuth token, compare email against FATHER_EMAIL env var
- [ ] T022 [US5] Update `web_ui/routes.py` — add all REST endpoints (GET /record, POST /rejection, POST /advance, POST /payslip, POST /email, POST /chat) with FATHER_EMAIL auth gate; keep public endpoints (GET /, GET /daily, GET /monthly, GET /workers, GET /worker/{name}, GET /products) open

**Checkpoint**: OAuth working, father sees all features, other users see read-only dashboard

---

## Phase 8: Integration & Polish

**Purpose**: Wire everything together, CLI testing, and quality assurance

- [ ] T023 Update `mcp_server.py` — register all 10 tools from their respective modules via FastMCP
- [ ] T024 [P] Create `tests/test_database.py` — test CRUD operations, unique constraints, validation rules for all 6 tables
- [ ] T025 [P] Create `tests/test_tools.py` — test each tool function with mock input, verify side effects
- [ ] T026 [P] Create `tests/test_agent.py` — test agent flow with sample Roman Urdu inputs, verify tool call consistency
- [ ] T027 Update `scheduler.py` — disable all auto-execution, keep only reminder comments per constitution Principle I
- [ ] T028 Update `main.py` — add new mode routing for `seed` command, verify all existing modes work with new database layer

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundation (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundation — first functional story
- **US2 (Phase 4)**: Depends on Foundation — no dependency on US1 (independent rejection/advance tables)
- **US3 (Phase 5)**: Depends on Foundation + US1 + US2 (needs production data + rejection + advances)
- **US4 (Phase 6)**: Depends on Foundation + US1 (needs production data for reports)
- **US5 (Phase 7)**: Depends on Foundation — independent of other stories
- **Integration (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundation — No dependencies on other stories 🎯 MVP
- **US2 (P2)**: Can start after Foundation — Independent of US1
- **US3 (P3)**: Depends on US1 + US2 (needs production + rejection + advance data)
- **US4 (P4)**: Depends on US1 (needs production data for reports)
- **US5 (P5)**: Can start after Foundation — Independent of all other stories

### Within Each Phase

- [P] tasks can run in parallel
- Models/CRUD before tools
- Tools before agent integration
- Story complete before moving to next priority

### Parallel Opportunities

```
Phase 2: T004 + T005 + T006 can run sequentially (database → seed → config)
Phase 3: T007 + T008 + T009 can run in parallel, then T010 depends on all three
Phase 4: T011 + T012 can run in parallel, then T013 depends on both
Phase 5: T014 + T015 can run in parallel, then T016 depends on both
Phase 6: T017 + T018 can run in parallel, then T019 depends on both
Phase 7: T020 + T021 can run in parallel, then T022 depends on both
Phase 8: T024 + T025 + T026 can run in parallel, T023+T027+T028 independent
```

---

## Parallel Execution Examples

```bash
# Phase 3 — Launch all US1 model/tool tasks in parallel:
Task: "Implement daily_log CRUD in tools/database.py"
Task: "Create tools/production_tools.py with log_production"
Task: "Update agent_system/data_extractor.py for Roman Urdu"

# Then — Agent integration (depends on all above):
Task: "Update agent_system/orchestrator.py — add US1 tools"
```

```bash
# Phase 4 — Launch rejection + advance tasks in parallel:
Task: "Create tools/rejection_tools.py"
Task: "Create tools/advance_tools.py"

# Then — Agent integration:
Task: "Update orchestrator.py — add US2 tools"
```

```bash
# Phase 5 — Launch report + payslip in parallel:
Task: "Create tools/report_tools.py"
Task: "Update tools/payslip_tools.py"

# Then — Agent integration:
Task: "Update orchestrator.py — add US3 tools"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundation (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Father can log production and see daily totals
5. Test via CLI: `python main.py agent` — say "Aj Kaleem ne 300 nut kiye"

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready (database working)
2. + Phase 3 (US1) → **MVP!** Production recording works
3. + Phase 4 (US2) → Rejection + advance tracking works
4. + Phase 5 (US3) → Payslip generation works
5. + Phase 6 (US4) → Manager email works
6. + Phase 7 (US5) → Auth + access control works
7. + Phase 8 → Full integration

### Parallel Team Strategy

With multiple developers:

1. **Foundation**: One developer completes Phase 1 + 2
2. **Once Foundation done**:
   - Developer A: US1 + US4 (both need production data)
   - Developer B: US2 + US3 (US3 depends on US2)
   - Developer C: US5 (fully independent) + Phase 8
3. Stories integrate independently at the end

---

## Notes

- All 28 functional requirements (FR-001 to FR-028) from spec.md are covered across these tasks
- [US1-P3] tasks are grouped by user story for independent completion
- T001-T003: Setup (no story labels)
- T004-T006: Foundation (no story labels — blocks all)
- T007-T028: Story-specific tasks with [USX] labels
- Each user story is independently testable per spec.md acceptance criteria
- No auto-execution anywhere — constitution Principle I enforced
- All manager reports: quantities-only, no financials — constitution Principle II enforced
