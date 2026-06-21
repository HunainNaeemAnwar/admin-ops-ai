import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from config import DATABASE_URL


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            rate REAL NOT NULL,
            tax_pct REAL DEFAULT 3.0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            entry_date TEXT NOT NULL,
            status TEXT DEFAULT 'present' CHECK(status IN ('present', 'absent')),
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (worker_id) REFERENCES workers(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(worker_id, product_id, entry_date)
        );

        CREATE TABLE IF NOT EXISTS rejections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            total_qty INTEGER NOT NULL CHECK(total_qty > 0),
            exclude_workers TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        );

        CREATE TABLE IF NOT EXISTS payslips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            gross_total REAL NOT NULL,
            tax_total REAL NOT NULL,
            rejection_deduction REAL DEFAULT 0,
            advance_deduction REAL DEFAULT 0,
            net_payable REAL NOT NULL,
            generated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (worker_id) REFERENCES workers(id),
            UNIQUE(worker_id, year, month)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_log_date ON daily_log(entry_date);
        CREATE INDEX IF NOT EXISTS idx_daily_log_worker ON daily_log(worker_id);
        CREATE INDEX IF NOT EXISTS idx_daily_log_worker_date ON daily_log(worker_id, entry_date);
        CREATE INDEX IF NOT EXISTS idx_rejections_month ON rejections(year, month);
        CREATE INDEX IF NOT EXISTS idx_advances_worker_month ON advances(worker_id, year, month);
    """)
    conn.commit()
    conn.close()


# ── Workers ──────────────────────────────────────────

def get_worker_id(name: str) -> Optional[int]:
    conn = get_db()
    row = conn.execute("SELECT id FROM workers WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row["id"] if row else None


def get_or_create_worker(name: str) -> int:
    wid = get_worker_id(name)
    if wid:
        return wid
    conn = get_db()
    cursor = conn.execute("INSERT INTO workers (name) VALUES (?)", (name,))
    conn.commit()
    wid = cursor.lastrowid
    conn.close()
    return wid


def get_all_workers() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, name, is_active FROM workers ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_workers() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, name FROM workers WHERE is_active = 1 ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Products ────────────────────────────────────────

def get_product_id(code: str) -> Optional[int]:
    conn = get_db()
    row = conn.execute("SELECT id FROM products WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row["id"] if row else None


def get_all_products() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, code, description, rate, tax_pct FROM products ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product_rate(code: str) -> Optional[float]:
    conn = get_db()
    row = conn.execute("SELECT rate FROM products WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row["rate"] if row else None


# ── Daily Log ────────────────────────────────────────

def log_production(worker_id: int, product_id: int, quantity: int, entry_date: str) -> int:
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO daily_log (worker_id, product_id, quantity, entry_date)
               VALUES (?, ?, ?, ?)""",
            (worker_id, product_id, quantity, entry_date),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise
    finally:
        conn.close()


def mark_absent(worker_id: int, entry_date: str) -> int:
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO daily_log (worker_id, product_id, quantity, entry_date, status)
               VALUES (?, (SELECT id FROM products LIMIT 1), 0, ?, 'absent')""",
            (worker_id, entry_date),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise
    finally:
        conn.close()


def update_entry(entry_id: int, quantity: int) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE daily_log SET quantity = ? WHERE id = ?",
        (quantity, entry_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_logs_for_date(entry_date: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT dl.id, dl.worker_id, w.name AS worker_name,
                  dl.product_id, p.code AS product_code, p.description,
                  dl.quantity, dl.entry_date, dl.status, dl.created_at
           FROM daily_log dl
           JOIN workers w ON w.id = dl.worker_id
           JOIN products p ON p.id = dl.product_id
           WHERE dl.entry_date = ?
           ORDER BY w.name""",
        (entry_date,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_logs_for_worker(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-31"
    rows = conn.execute(
        """SELECT dl.id, dl.quantity, dl.entry_date, dl.status,
                  p.code AS product_code, p.description
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.worker_id = ? AND dl.entry_date BETWEEN ? AND ?
           ORDER BY dl.entry_date""",
        (worker_id, start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ensure_day_complete(entry_date: str, worker_ids: list[int]) -> list[int]:
    conn = get_db()
    placeholders = ",".join("?" * len(worker_ids))
    rows = conn.execute(
        f"""SELECT DISTINCT worker_id FROM daily_log
             WHERE entry_date = ? AND worker_id IN ({placeholders})""",
        [entry_date] + worker_ids,
    ).fetchall()
    conn.close()
    recorded = {r["worker_id"] for r in rows}
    return [wid for wid in worker_ids if wid not in recorded]


# ── Rejections ──────────────────────────────────────

def log_rejection(year: int, month: int, product_id: int, total_qty: int, exclude_workers: Optional[list[str]] = None) -> int:
    conn = get_db()
    import json
    exclude_json = json.dumps(exclude_workers or [])
    cursor = conn.execute(
        """INSERT INTO rejections (year, month, product_id, total_qty, exclude_workers)
           VALUES (?, ?, ?, ?, ?)""",
        (year, month, product_id, total_qty, exclude_json),
    )
    conn.commit()
    rid = cursor.lastrowid
    conn.close()
    return rid


def get_rejections_for_month(year: int, month: int) -> list[dict]:
    conn = get_db()
    import json
    rows = conn.execute(
        """SELECT r.id, r.year, r.month, r.product_id, p.code AS product_code,
                  r.total_qty, r.exclude_workers, r.created_at
           FROM rejections r
           JOIN products p ON p.id = r.product_id
           WHERE r.year = ? AND r.month = ?
           ORDER BY r.id""",
        (year, month),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["exclude_workers"] = json.loads(d.get("exclude_workers", "[]"))
        result.append(d)
    return result


def get_worker_rejection_share(worker_name: str, year: int, month: int) -> dict[str, int]:
    conn = get_db()
    import json
    rows = conn.execute(
        """SELECT r.product_id, p.code AS product_code, r.total_qty, r.exclude_workers
           FROM rejections r
           JOIN products p ON p.id = r.product_id
           WHERE r.year = ? AND r.month = ?""",
        (year, month),
    ).fetchall()
    conn.close()

    active = get_active_workers()
    active_names = [w["name"] for w in active]
    shares = {}
    for r in rows:
        exclude = json.loads(r["exclude_workers"])
        eligible = [n for n in active_names if n not in exclude]
        if worker_name in exclude or not eligible:
            shares[r["product_code"]] = 0
        else:
            base = r["total_qty"] // len(eligible)
            remainder = r["total_qty"] % len(eligible)
            idx = eligible.index(worker_name)
            shares[r["product_code"]] = base + (1 if idx < remainder else 0)
    return shares


# ── Advances ─────────────────────────────────────────

def record_advance(worker_id: int, amount: float, year: int, month: int, description: str = "") -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO advances (worker_id, amount, month, year, description)
           VALUES (?, ?, ?, ?, ?)""",
        (worker_id, amount, month, year, description),
    )
    conn.commit()
    aid = cursor.lastrowid
    conn.close()
    return aid


def get_advances_for_worker_month(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT id, amount, description, created_at
           FROM advances
           WHERE worker_id = ? AND year = ? AND month = ?
           ORDER BY created_at""",
        (worker_id, year, month),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_advances_for_worker_month(worker_id: int, year: int, month: int) -> float:
    conn = get_db()
    row = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total
           FROM advances
           WHERE worker_id = ? AND year = ? AND month = ?""",
        (worker_id, year, month),
    ).fetchone()
    conn.close()
    return row["total"] if row else 0.0


# ── Payslips ─────────────────────────────────────────

def save_payslip(
    worker_id: int, year: int, month: int,
    gross_total: float, tax_total: float,
    rejection_deduction: float, advance_deduction: float,
    net_payable: float,
) -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT OR REPLACE INTO payslips
           (worker_id, year, month, gross_total, tax_total, rejection_deduction, advance_deduction, net_payable)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (worker_id, year, month, gross_total, tax_total, rejection_deduction, advance_deduction, net_payable),
    )
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid


def get_payslip(worker_id: int, year: int, month: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM payslips
           WHERE worker_id = ? AND year = ? AND month = ?""",
        (worker_id, year, month),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Summary helpers ──────────────────────────────────

def get_daily_totals(entry_date: str) -> dict:
    conn = get_db()
    rows = conn.execute(
        """SELECT p.code AS product_code, SUM(dl.quantity) AS total_qty
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.entry_date = ? AND dl.status = 'present'
           GROUP BY p.code""",
        (entry_date,),
    ).fetchall()
    conn.close()
    return {r["product_code"]: r["total_qty"] for r in rows}


def get_worker_month_production(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-31"
    rows = conn.execute(
        """SELECT p.code AS product_code, dl.quantity, dl.entry_date
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.worker_id = ? AND dl.entry_date BETWEEN ? AND ? AND dl.status = 'present'
           ORDER BY dl.entry_date""",
        (worker_id, start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
