# Database Schema Contract: Backend Core System

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22

## SQLite DDL

```sql
-- ============================================================
-- Workers
-- ============================================================
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- Products
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    rate REAL NOT NULL,
    tax_pct REAL DEFAULT 3.0,
    active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- Daily Production Log
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    worker_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,
    is_absent BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(date, worker_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_log_date ON daily_log(date);
CREATE INDEX IF NOT EXISTS idx_daily_log_worker ON daily_log(worker_id);
CREATE INDEX IF NOT EXISTS idx_daily_log_product ON daily_log(product_id);

-- ============================================================
-- Monthly Rejections (Department Level)
-- ============================================================
CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    total_qty INTEGER NOT NULL,
    excluded_workers TEXT DEFAULT '[]',
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id),
    UNIQUE(year, month, product_id)
);

-- ============================================================
-- Advance Payments
-- ============================================================
CREATE TABLE IF NOT EXISTS advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

-- ============================================================
-- Payslips (Cached Monthly Summaries)
-- ============================================================
CREATE TABLE IF NOT EXISTS payslips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_gross REAL,
    total_pieces INTEGER,
    rejection_deduction REAL,
    advance_deduction REAL,
    tax_deduction REAL,
    net_payable REAL,
    generated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    UNIQUE(worker_id, year, month)
);

-- Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;
```

## PostgreSQL Migration Notes

When moving to Neon PostgreSQL:

1. Replace `INTEGER PRIMARY KEY AUTOINCREMENT` with `SERIAL PRIMARY KEY`
2. Replace `TEXT DEFAULT (datetime('now'))` with `TIMESTAMP DEFAULT NOW()`
3. Replace `datetime('now')` with `NOW()` in all expressions
4. Replace `TEXT` dates with `DATE` type
5. Replace JSON text field with `JSONB` for `excluded_workers`
6. Use `CREATE INDEX CONCURRENTLY` for zero-downtime migration
