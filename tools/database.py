import sqlite3
import threading
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Optional

from config import DATABASE_URL
from tools.cache import cached_workers, cached_products

_local = threading.local()


def _is_conn_alive(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1")
        return True
    except sqlite3.ProgrammingError:
        return False


def close_db():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def get_db() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None or not _is_conn_alive(conn):
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
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
            reason TEXT DEFAULT '',
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
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(year, month, product_id)
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

        CREATE TABLE IF NOT EXISTS advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        );

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

        CREATE INDEX IF NOT EXISTS idx_daily_log_date ON daily_log(entry_date);
        CREATE INDEX IF NOT EXISTS idx_daily_log_worker ON daily_log(worker_id);
        CREATE INDEX IF NOT EXISTS idx_daily_log_worker_date ON daily_log(worker_id, entry_date);
        CREATE INDEX IF NOT EXISTS idx_rejections_month ON rejections(year, month);
        CREATE INDEX IF NOT EXISTS idx_advances_worker_month ON advances(worker_id, year, month);
    """)
    try:
        conn.execute("ALTER TABLE daily_log ADD COLUMN reason TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()


# ── Workers ──────────────────────────────────────────

def get_worker_id(name: str) -> Optional[int]:
    conn = get_db()
    row = conn.execute("SELECT id FROM workers WHERE name = ?", (name,)).fetchone()
    return row["id"] if row else None


def get_or_create_worker(name: str) -> int:
    from tools.cache import invalidate_worker_cache
    wid = get_worker_id(name)
    if wid:
        return wid
    conn = get_db()
    cursor = conn.execute("INSERT INTO workers (name) VALUES (?)", (name,))
    conn.commit()
    wid = cursor.lastrowid
    invalidate_worker_cache()
    return wid


@cached_workers
def get_all_workers() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, name, is_active FROM workers ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@cached_workers
def get_active_workers() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, name FROM workers WHERE is_active = 1 ORDER BY name").fetchall()
    return [dict(r) for r in rows]


# ── Products ────────────────────────────────────────

def get_product_id(code: str) -> Optional[int]:
    conn = get_db()
    row = conn.execute("SELECT id FROM products WHERE code = ?", (code,)).fetchone()
    return row["id"] if row else None


@cached_products
def get_all_products() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, code, description, rate, tax_pct FROM products ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_product_rate(code: str) -> Optional[float]:
    conn = get_db()
    row = conn.execute("SELECT rate FROM products WHERE code = ?", (code,)).fetchone()
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
        raise


def mark_absent(worker_id: int, entry_date: str, reason: str = "") -> int:
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO daily_log (worker_id, product_id, quantity, entry_date, status, reason)
               VALUES (?, (SELECT id FROM products LIMIT 1), 0, ?, 'absent', ?)""",
            (worker_id, entry_date, reason),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise


def update_entry(entry_id: int, quantity: int) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE daily_log SET quantity = ? WHERE id = ?",
        (quantity, entry_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
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
    return [dict(r) for r in rows]


def get_logs_for_worker(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    days = monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{days:02d}"
    rows = conn.execute(
        """SELECT dl.id, dl.quantity, dl.entry_date, dl.status,
                  p.code AS product_code, p.description
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.worker_id = ? AND dl.entry_date BETWEEN ? AND ?
           ORDER BY dl.entry_date""",
        (worker_id, start, end),
    ).fetchall()
    return [dict(r) for r in rows]



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
    return [dict(r) for r in rows]


def get_total_advances_for_worker_month(worker_id: int, year: int, month: int) -> float:
    conn = get_db()
    row = conn.execute(
        """SELECT COALESCE(SUM(amount), 0) AS total
           FROM advances
           WHERE worker_id = ? AND year = ? AND month = ?""",
        (worker_id, year, month),
    ).fetchone()
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
    return pid


def get_payslip(worker_id: int, year: int, month: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM payslips
           WHERE worker_id = ? AND year = ? AND month = ?""",
        (worker_id, year, month),
    ).fetchone()
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
    return {r["product_code"]: r["total_qty"] for r in rows}


def get_worker_month_production(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    days = monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{days:02d}"
    rows = conn.execute(
        """SELECT p.code AS product_code, dl.quantity, dl.entry_date
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.worker_id = ? AND dl.entry_date BETWEEN ? AND ? AND dl.status = 'present'
           ORDER BY dl.entry_date""",
        (worker_id, start, end),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Worker Dashboard ────────────────────────────────

def get_worker_daily_breakdown(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    days_in_month = monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{days_in_month:02d}"

    rows = conn.execute(
        """SELECT dl.entry_date, dl.status, dl.reason, p.code AS product_code, dl.quantity
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.worker_id = ? AND dl.entry_date BETWEEN ? AND ?
           ORDER BY dl.entry_date, p.code""",
        (worker_id, start, end),
    ).fetchall()

    products = get_all_products()
    product_codes = [p["code"] for p in products]

    date_entries: dict[str, dict] = {}
    for r in rows:
        d = dict(r)
        dt = d["entry_date"]
        if dt not in date_entries:
            date_entries[dt] = {"products": {}, "status": "no_data", "reason": ""}
        if d["status"] == "absent":
            date_entries[dt]["status"] = "absent"
            if d.get("reason"):
                date_entries[dt]["reason"] = d["reason"]
        else:
            date_entries[dt]["status"] = "present"
            date_entries[dt]["products"][d["product_code"]] = d["quantity"]

    result = []
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        if date_str in date_entries:
            entry = date_entries[date_str]
            if entry["status"] == "absent":
                result.append({"date": date_str, "status": "absent", "reason": entry["reason"], "products": {}})
            else:
                full_products = {code: entry["products"].get(code, 0) for code in product_codes}
                result.append({"date": date_str, "status": "present", "reason": "", "products": full_products})
        else:
            result.append({
                "date": date_str,
                "status": "no_data",
                "reason": "",
                "products": {code: 0 for code in product_codes},
            })

    return result


def is_month_archived(year: int, month: int) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) > 0 AS cnt FROM worker_monthly_history WHERE year = ? AND month = ?",
        (year, month),
    ).fetchone()
    return bool(row["cnt"])


def insert_worker_history(worker_id: int, year: int, month: int, product_id: int, total_quantity: int, gross_amount: float) -> Optional[int]:
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO worker_monthly_history
               (worker_id, year, month, product_id, total_quantity, gross_amount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (worker_id, year, month, product_id, total_quantity, gross_amount),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_worker_history_month(worker_id: int, year: int, month: int) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT wmh.total_quantity, wmh.gross_amount, p.code AS product_code
           FROM worker_monthly_history wmh
           JOIN products p ON p.id = wmh.product_id
           WHERE wmh.worker_id = ? AND wmh.year = ? AND wmh.month = ?
           ORDER BY p.code""",
        (worker_id, year, month),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_history_months() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT year, month FROM worker_monthly_history
           ORDER BY year DESC, month DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def backfill_history(year: int | None = None, month: int | None = None) -> dict:
    conn = get_db()
    products = get_all_products()
    workers = get_active_workers()

    date_filter = ""
    params: list[str] = []
    if year is not None and month is not None:
        date_filter = "AND dl.entry_date BETWEEN ? AND ?"
        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        params = [f"{year}-{month:02d}-01", f"{year}-{month:02d}-{days_in_month:02d}"]

    rows = conn.execute(
        f"""SELECT DISTINCT dl.worker_id, dl.entry_date, p.code AS product_code, p.id AS product_id, dl.quantity
            FROM daily_log dl
            JOIN products p ON p.id = dl.product_id
            WHERE dl.quantity > 0 {date_filter}
            ORDER BY dl.worker_id, dl.entry_date, p.code""",
        params,
    ).fetchall()

    if not rows:
        return {"status": "ok", "message": "No production data to backfill", "count": 0, "months": []}

    worker_months: dict[tuple[int, int, int], dict[int, int]] = {}
    for r in rows:
        d = dict(r)
        ym = (d["entry_date"][:4], d["entry_date"][5:7])
        key = (d["worker_id"], int(ym[0]), int(ym[1]))
        if key not in worker_months:
            worker_months[key] = {}
        pid = d["product_id"]
        worker_months[key][pid] = worker_months[key].get(pid, 0) + d["quantity"]

    count = 0
    archived_months = set()
    for (wid, y, m), prods in worker_months.items():
        for p in products:
            qty = prods.get(p["id"], 0)
            if qty > 0:
                gross = qty * p["rate"]
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO worker_monthly_history
                       (worker_id, year, month, product_id, total_quantity, gross_amount)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (wid, y, m, p["id"], qty, gross),
                )
                if cursor.lastrowid:
                    count += 1
        archived_months.add((y, m))
    conn.commit()

    from tools.export_tools import generate_worker_excel
    for (y, m) in archived_months:
        for w in workers:
            generate_worker_excel(w["name"], y, m)

    return {
        "status": "ok",
        "message": f"Backfilled {count} history records across {len(archived_months)} month(s)",
        "count": count,
        "months": [{"year": y, "month": m} for y, m in sorted(archived_months)],
    }
