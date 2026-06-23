# Implementation Plan: Worker Dashboard + History Auto-Archive

**Branch**: `003-worker-dashboard-history` | **Date**: 2026-06-23 | **Spec**: specs/003-worker-dashboard-history/spec.md
**Input**: Feature specification from specs/003-worker-dashboard-history/spec.md

## Summary

Build a public worker dashboard at `/` showing monthly production calendar table (dates × products) with worker/month dropdowns and individual Excel download. Move father's OAuth-protected management dashboard to `/admin`. Implement auto-archive on month rollover (1st day of new month) — aggregate daily_log into a history table and generate per-worker Excel files for the previous month.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, openpyxl, sqlite3 (stdlib)
**Storage**: SQLite (existing) + new `worker_monthly_history` table + `data/history/` directory for archived Excel files
**Testing**: Manual browser testing + pytest for archive/query functions
**Target Platform**: Linux server (FastAPI web)
**Project Type**: Single Python monolith (existing structure)
**Performance Goals**: Dashboard loads in <2s, Excel download in <3s, archive all 8 workers in <10s
**Constraints**: No auth on `/`, father features at `/admin` with existing OAuth, no regression in existing tools
**Scale/Scope**: 8 workers, single father operator, public dashboard for factory floor

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Assessment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Father-Triggered Control | ⚠️ PARTIAL | Auto-archive on month rollover is automatic. Exception justified — archive is read-only (Excel + history table), no email/payslip auto-sent. Father still controls all management actions. |
| II. Manager Reporting | ✅ PASS | No changes to manager reporting. Worker dashboard shows only production data, no financial info. |
| III. Database-First Persistence | ✅ PASS | New `worker_monthly_history` table extends the SQLite schema. Excel remains export-only. |
| IV. Complete Daily Tracking | ✅ PASS | Not affected. Daily tracking continues unchanged. |
| V. Simple Product Model | ✅ PASS | Not affected. Same 5 product codes. |
| VI. Auth & Access Control | ✅ PASS | Worker dashboard is public (intentional — no sensitive data). Father dashboard at `/admin` retains OAuth. |

**Note on Principle I violation**: Auto-archive is a one-time, read-only aggregation at month boundary. It does not send emails, generate payslips, or modify live production data. This is the minimum automation needed to maintain clean month-to-month transitions.

## Project Structure

### Documentation (this feature)

```text
specs/003-worker-dashboard-history/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 — decisions
├── data-model.md        # Phase 1 — history table schema
├── quickstart.md        # Phase 1 — updated setup guide
├── contracts/           # Phase 1 — API contracts
│   └── endpoints.md     # New routes contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Task breakdown
```

### Source Code (repository root)

```text
web_ui/
├── routes.py            # MODIFY: / → worker dashboard, /admin → father panel
└── templates/
    ├── index.html       # Move to admin_panel.html (or update for /admin)
    └── worker_dashboard.html  # NEW: monthly calendar table

tools/
├── database.py          # MODIFY: add history table CRUD + daily breakdown query
└── export_tools.py      # MODIFY: add generate_worker_excel()

data/
└── history/             # NEW: archived monthly Excel files

config.py                # MODIFY: add HISTORY_DIR path
```

**Structure Decision**: Pure addition to existing single-project structure. No new entry points, no external dependencies.

## Complexity Tracking

No constitutional violations beyond the noted Principle I exception (auto-archive). No complexity tracking needed.

## Phase 0: Research

### Research Tasks

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Worker dashboard auth | Public (no auth) | Workers have no passwords; data is production quantities only (no financials) |
| Route structure | `/` = worker, `/admin` = father | Clean separation; father path is clearly administrative |
| History table schema | `worker_monthly_history(worker_id, year, month, product_id, total_quantity, gross_amount)` | Per-product aggregation enables exact reconstruction of monthly totals |
| Archive trigger | Dashboard visit on/after month 1st | No scheduler needed; piggybacks on natural traffic |
| Idempotency check | `SELECT COUNT(*) FROM worker_monthly_history WHERE year=? AND month=?` | Simple EXISTS check before archive |
| Excel per worker | Reuse existing openpyxl infrastructure | `export_tools.py` already has _style_header, _thin_border helpers |
| Absent days in table | Check daily_log.status for that date | If status='absent' for all products on a date, mark row as ABSENT |

## Phase 1: Design

### Data Model — New Table

```sql
CREATE TABLE IF NOT EXISTS worker_monthly_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL,
    gross_amount REAL NOT NULL,
    archived_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(worker_id, year, month, product_id)
);

CREATE INDEX IF NOT EXISTS idx_history_worker_month
    ON worker_monthly_history(worker_id, year, month);
```

### API Contracts — New/Modified Routes

| Method | Path | Purpose | Auth | Behavior Change |
|--------|------|---------|------|-----------------|
| GET | `/` | Worker dashboard (public) | None | **NEW**: Monthly calendar table + dropdowns |
| GET | `/admin` | Father dashboard | OAuth | **MODIFIED**: Was `/`, now at `/admin` |
| GET | `/admin/...` | All father operations | OAuth | **MODIFIED**: Prefix `/admin` |
| GET | `/api/worker/{name}/month/{year}/{month}` | Worker month data (JSON) | None | **NEW**: Returns daily breakdown for table |
| GET | `/api/worker/{name}/excel/{year}/{month}` | Download worker Excel | None | **NEW**: Generates + returns Excel file |
| GET | `/api/history/check` | Check if archive needed | None | **NEW**: Returns {archive_needed, prev_month} |

### Worker Dashboard Data Flow

```
1. Browser hits /
2. Server renders worker_dashboard.html with:
   - workers list (from DB)
   - products list (from DB)
   - current month/year
3. JavaScript loads:
   - On page load: fetch /api/worker/{first}/{year}/{month} → JSON
   - Render table with dates as rows, products as columns
4. On dropdown change:
   - Fetch new data JSON
   - Re-render table
5. On "Download Excel" click:
   - GET /api/worker/{name}/excel/{year}/{month} → file download
```

### Auto-Archive Flow

```
1. Any visit to / (or /api/history/check)
2. Check: today.day == 1? AND archive exists for (prev_year, prev_month)?
3. If YES:
   a. For each worker × product: aggregate daily_log SUM(quantity)
   b. INSERT into worker_monthly_history
   c. Generate Excel for each worker → data/history/
   d. Set flag (archive complete)
4. If NO: skip
```

### Worker Daily Breakdown Query

```python
def get_worker_daily_breakdown(worker_id: int, year: int, month: int) -> list[dict]:
    """Returns per-day data with product quantities pivoted.

    Returns:
        [
            {"date": "2026-06-01", "products": {"NUT": 300, "10*20": 150, ...}, "status": "present"},
            {"date": "2026-06-03", "status": "absent"},
            ...
        ]

    For archived months, reads from worker_monthly_history.
    For current month, reads from daily_log.
    """
```

### Worker Excel Export

```python
def generate_worker_excel(worker_name: str, year: int, month: int) -> str:
    """Generates per-worker monthly Excel with daily breakdown.

    Format: dates as rows, products as columns, totals row.
    Absent days marked in red.
    Returns file path.
    """
```

## Constitution Re-check

All gates remain passing post-design. The auto-archive exception is documented and justified.

## Next Steps

Proceed to `/sp.tasks` for task breakdown with parallel execution opportunities.
