# Data Model: Backend Core System — Phase 1

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22

## Entity-Relationship Diagram

```
workers ──┬──< daily_log >── products
          │
          ├──< advances
          │
          ├──< payslips
          │
rejections (department-level, no direct FK to workers)
```

## Core Tables

### 1. workers

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unique ID |
| name | TEXT | UNIQUE, NOT NULL | Worker name (e.g., "Kaleem") |
| active | BOOLEAN | DEFAULT 1 | Whether worker is currently active |
| created_at | TEXT | DEFAULT datetime('now') | Row creation timestamp |

**Seed data**: 8 fixed workers from `FIXED_WORKERS` env var.

### 2. products

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unique ID |
| name | TEXT | UNIQUE, NOT NULL | Product code (e.g., "NUT", "10*20") |
| rate | REAL | NOT NULL | Per-piece rate in Rs |
| tax_pct | REAL | DEFAULT 3.0 | Tax percentage |
| active | BOOLEAN | DEFAULT 1 | Whether product is currently in production |
| created_at | TEXT | DEFAULT datetime('now') | Row creation timestamp |

**Seed data**: 5 products from env vars (`RATE_NUT`, `RATE_10X20`, etc.).

### 3. daily_log

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unique entry ID |
| date | TEXT | NOT NULL | Date in "YYYY-MM-DD" format |
| worker_id | INTEGER | FK → workers.id, NOT NULL | Worker reference |
| product_id | INTEGER | FK → products.id, NOT NULL | Product reference |
| quantity | INTEGER | DEFAULT 0 | Pieces produced (0 = worked but not this product) |
| is_absent | BOOLEAN | DEFAULT 0 | TRUE = worker was on leave |
| notes | TEXT | NULLABLE | Optional notes |
| created_at | TEXT | DEFAULT datetime('now') | Row creation timestamp |
| updated_at | TEXT | DEFAULT datetime('now') | Last update timestamp |

**Unique constraint**: (date, worker_id, product_id)
**Indexes**: date, worker_id, product_id

**Validation rules**:
- If `is_absent = TRUE`, then `quantity` MUST be 0
- If `is_absent = FALSE`, `quantity` can be 0 (worked but didn't make this product)
- `date` MUST NOT be in the future
- Every worker MUST have a row for every date (either data or absent)

### 4. rejections

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unique rejection ID |
| year | INTEGER | NOT NULL | Year (e.g., 2026) |
| month | INTEGER | NOT NULL | Month 1-12 |
| product_id | INTEGER | FK → products.id, NOT NULL | Product reference |
| total_qty | INTEGER | NOT NULL | Total rejected quantity |
| excluded_workers | TEXT | DEFAULT '[]' | JSON array of excluded worker IDs |
| description | TEXT | NULLABLE | Optional description |
| created_at | TEXT | DEFAULT datetime('now') | Row creation timestamp |

**Unique constraint**: (year, month, product_id)

**Distribution logic**:
```
active_workers = count of active workers
excluded_workers = JSON.loads(excluded_workers)
affected_workers = active_workers - len(excluded_workers)
per_worker_share = total_qty / affected_workers
```

### 5. advances

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unique advance ID |
| worker_id | INTEGER | FK → workers.id, NOT NULL | Worker reference |
| amount | REAL | NOT NULL | Advance amount in Rs |
| date | TEXT | NOT NULL | Date advance was given |
| month | INTEGER | NOT NULL | Month to deduct from |
| year | INTEGER | NOT NULL | Year to deduct from |
| description | TEXT | NULLABLE | Optional description |
| created_at | TEXT | DEFAULT datetime('now') | Row creation timestamp |

### 6. payslips

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unique payslip ID |
| worker_id | INTEGER | FK → workers.id, NOT NULL | Worker reference |
| year | INTEGER | NOT NULL | Year |
| month | INTEGER | NOT NULL | Month |
| total_gross | REAL | NOT NULL | Total gross earnings |
| total_pieces | INTEGER | NOT NULL | Total pieces produced |
| rejection_deduction | REAL | NOT NULL | Rejection amount deducted |
| advance_deduction | REAL | NOT NULL | Advance amount deducted |
| tax_deduction | REAL | NOT NULL | Tax amount deducted |
| net_payable | REAL | NOT NULL | Final payable amount |
| generated_at | TEXT | DEFAULT datetime('now') | Generation timestamp |

**Unique constraint**: (worker_id, year, month)

**Calculation**:
```
gross = Σ(rate × quantity) per product
rejection_deduction = Σ(rate × reject_share) per product
advance_deduction = Σ(advances.amount) for this worker/month/year
taxable = gross - rejection_deduction
tax_deduction = taxable × TAX_PERCENTAGE / 100
net_payable = gross - rejection_deduction - advance_deduction - tax_deduction
```

## State Transitions

### Daily Log Lifecycle

```
[No entry] → log_production() → [Has entry with quantities]
[No entry] → mark_absent()    → [Has entry with is_absent=TRUE]
[Any entry] → update_entry()  → [Updated entry with audit trail]
```

### Rejection Lifecycle

```
[No rejection] → log_rejection() → [Rejection recorded with equal distribution]
[Has rejection] → exclude_worker() → [Recalculated distribution]
[Has rejection] → log_rejection() → [Multiple rejections summed per product]
```

### Payslip Lifecycle

```
[No payslip] → generate_payslip() → [PDF + Excel created]
[Has payslip] → edit entry → regenerate_payslip() → [Updated PDF + Excel]
```
