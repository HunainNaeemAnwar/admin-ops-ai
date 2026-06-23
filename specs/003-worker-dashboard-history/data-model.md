# Data Model: Worker Dashboard + History Auto-Archive

**Branch**: `003-worker-dashboard-history` | **Date**: 2026-06-23

## New Table

### worker_monthly_history

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

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | PK, AUTOINCREMENT |
| worker_id | INTEGER | FK → workers.id |
| year | INTEGER | Archive year (e.g., 2026) |
| month | INTEGER | Archive month (1-12) |
| product_id | INTEGER | FK → products.id |
| total_quantity | INTEGER | SUM of daily_log.quantity for this worker×product×month |
| gross_amount | REAL | total_quantity × product.rate (for payslip reference) |
| archived_at | TEXT | Timestamp of archival |

**Unique constraint**: (worker_id, year, month, product_id)

**Relationship**: Every row in `worker_monthly_history` corresponds to aggregated data from `daily_log` for one worker × one product × one month.

## New Directory

```
data/
└── history/          # Archived monthly Excel files
```

**Naming convention**: `data/history/{worker_name}_{year}_{month:02d}.xlsx`
Example: `data/history/Kaleem_2026_06.xlsx`

## State Transitions

### Archive Lifecycle

```
Month is live (current) → Month ends → Next month 1st day:
  1. daily_log aggregated per worker × product
  2. INSERT into worker_monthly_history
  3. Generate Excel → data/history/
  4. Dashboard now shows history data for that month
```

### Dashboard Data Source

```
Current month (year == current_year AND month == current_month):
  → Read from daily_log (live data)

Previous months (archived):
  → Read from worker_monthly_history (snapshot data)

Future months (no data):
  → Return empty table with "No production data" message
```
