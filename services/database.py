import sqlite3
import threading
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Optional

from config import DATABASE_URL
from services.cache import cached_workers, cached_products

_local = threading.local()
_memory_local = threading.local()

MEMORY_DB_DIR = Path("data/agent_memory")
MEMORY_DB = str(MEMORY_DB_DIR / "agent_memory.db")


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
        conn = sqlite3.connect(DATABASE_URL, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def get_memory_db() -> sqlite3.Connection:
    conn = getattr(_memory_local, "conn", None)
    if conn is None or not _is_conn_alive(conn):
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _memory_local.conn = conn
    return conn


def init_memory_db():
    MEMORY_DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_memory_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_data TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_messages_session
            ON chat_messages(session_id, id)
    """)
    conn.commit()

    row = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()
    if row and row[0] == 0:
        try:
            legacy = sqlite3.connect(DATABASE_URL, timeout=5)
            has_table = legacy.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'"
            ).fetchone()
            if has_table:
                rows = legacy.execute(
                    "SELECT session_id, message_data, created_at FROM chat_messages"
                ).fetchall()
                if rows:
                    conn.executemany(
                        "INSERT INTO chat_messages (session_id, message_data, created_at) VALUES (?, ?, ?)",
                        rows,
                    )
                    conn.commit()
                    print(f"[DB] Migrated {len(rows)} chat messages to agent_memory.db")
            legacy.close()
        except Exception as e:
            print(f"[DB] No legacy chat data to migrate: {e}")


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
        CREATE INDEX IF NOT EXISTS idx_daily_log_date_status ON daily_log(entry_date, status);
        CREATE INDEX IF NOT EXISTS idx_rejections_month ON rejections(year, month);
        CREATE INDEX IF NOT EXISTS idx_advances_worker_month ON advances(worker_id, year, month);
        CREATE INDEX IF NOT EXISTS idx_advances_worker_month_amount ON advances(worker_id, year, month, amount);
        CREATE INDEX IF NOT EXISTS idx_advances_month ON advances(year, month);
        CREATE INDEX IF NOT EXISTS idx_history_year_month ON worker_monthly_history(year, month);

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            ip_address TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            revoked INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS auth_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            action TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            code_verifier TEXT NOT NULL,
            redirect_uri TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions(email);
        CREATE INDEX IF NOT EXISTS idx_auth_log_email ON auth_log(email);
        CREATE INDEX IF NOT EXISTS idx_auth_log_created ON auth_log(created_at);
        CREATE INDEX IF NOT EXISTS idx_oauth_states_created ON oauth_states(created_at);
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
    from services.cache import invalidate_worker_cache
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
    updated = conn.execute(
        "UPDATE daily_log SET status = 'absent', reason = ? WHERE worker_id = ? AND entry_date = ?",
        (reason, worker_id, entry_date),
    ).rowcount
    if updated == 0:
        cursor = conn.execute(
            """INSERT INTO daily_log (worker_id, product_id, quantity, entry_date, status, reason)
               VALUES (?, (SELECT id FROM products WHERE code = 'NUT'), 0, ?, 'absent', ?)""",
            (worker_id, entry_date, reason),
        )
        conn.commit()
        return cursor.lastrowid
    conn.commit()
    return 0


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
                  dl.quantity, dl.entry_date, dl.status, dl.reason, dl.created_at
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
        if worker_name in exclude or not eligible or worker_name not in eligible:
            shares[r["product_code"]] = 0
        else:
            denominator = len(eligible)
            if denominator == 0:
                shares[r["product_code"]] = 0
            else:
                base = r["total_qty"] // denominator
                remainder = r["total_qty"] % denominator
                idx = eligible.index(worker_name)
                shares[r["product_code"]] = base + (1 if idx < remainder else 0)
    return shares


# ── Advances ─────────────────────────────────────────

def record_advance(worker_id: int, amount: float, year: int, month: int, description: str = "") -> int:
    conn = get_db()
    from datetime import date
    entry_date = date(year, month, 1).isoformat() if year and month else date.today().isoformat()
    cursor = conn.execute(
        """INSERT INTO advances (worker_id, amount, date, month, year, description)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (worker_id, amount, entry_date, month, year, description),
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


def get_all_advances_for_month(year: int, month: int) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT a.worker_id, w.name AS worker_name, a.amount, a.description, a.created_at
           FROM advances a
           JOIN workers w ON w.id = a.worker_id
           WHERE a.year = ? AND a.month = ?
           ORDER BY w.name, a.created_at""",
        (year, month),
    ).fetchall()
    return [dict(r) for r in rows]


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


def get_date_range_totals(start_date: str, end_date: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT dl.entry_date, p.code AS product_code, SUM(dl.quantity) AS total_qty
           FROM daily_log dl
           JOIN products p ON p.id = dl.product_id
           WHERE dl.entry_date BETWEEN ? AND ? AND dl.status = 'present'
           GROUP BY dl.entry_date, p.code
           ORDER BY dl.entry_date""",
        (start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def _extract_text(item: dict) -> str:
    content = item.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", "") or block.get("content", "") or "")
        return "\n".join(parts).strip()
    return str(content)


def load_chat_messages(session_id: str) -> list:
    conn = get_memory_db()
    rows = conn.execute(
        "SELECT message_data FROM chat_messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    import json
    items = []
    for (msg,) in rows:
        try:
            item = json.loads(msg)
            if item.get("role") and _extract_text(item):
                items.append(item)
        except (json.JSONDecodeError, TypeError):
            continue
    return items


def save_chat_messages(session_id: str, messages: list):
    if not messages:
        return
    import json, time
    for attempt in range(5):
        try:
            conn = get_memory_db()
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            for msg in messages:
                if msg.get("role") in ("tool", "function"):
                    continue
                if not msg.get("role"):
                    continue
                if not _extract_text(msg):
                    continue
                conn.execute(
                    "INSERT INTO chat_messages (session_id, message_data) VALUES (?, ?)",
                    (session_id, json.dumps(msg)),
                )
            conn.commit()
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < 4:
                time.sleep(0.5)
                continue
            raise


def delete_chat_messages(session_id: str):
    conn = get_memory_db()
    conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    conn.commit()


def delete_logs_for_date(entry_date: str) -> dict:
    conn = get_db()
    cur = conn.execute("DELETE FROM daily_log WHERE entry_date = ?", (entry_date,))
    conn.commit()
    return {"deleted_rows": cur.rowcount, "entry_date": entry_date}


def list_chat_sessions(limit: int = 20) -> list[dict]:
    import json
    conn = get_memory_db()
    rows = conn.execute("""
        SELECT cm.session_id,
               MIN(cm.created_at) as created_at,
               MAX(cm.created_at) as last_activity,
               COUNT(*) as message_count,
               (SELECT message_data FROM chat_messages
                WHERE session_id = cm.session_id
                ORDER BY id LIMIT 1) as preview
        FROM chat_messages cm
        GROUP BY cm.session_id
        ORDER BY last_activity DESC
        LIMIT ?
    """, (limit,)).fetchall()
    sessions = []
    for r in rows:
        first_text = ""
        if r["preview"]:
            try:
                d = json.loads(r["preview"])
                first_text = d.get("content", "")[:80]
            except Exception:
                pass
        sessions.append({
            "session_id": r["session_id"],
            "created_at": r["created_at"],
            "last_activity": r["last_activity"],
            "message_count": r["message_count"],
            "preview": first_text,
        })
    return sessions


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


def get_all_workers_month_production(year: int, month: int) -> list[dict]:
    conn = get_db()
    start = f"{year}-{month:02d}-01"
    from calendar import monthrange
    days = monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{days:02d}"
    rows = conn.execute(
        """SELECT dl.worker_id, w.name AS worker_name, p.code AS product_code, SUM(dl.quantity) AS total_qty
           FROM daily_log dl
           JOIN workers w ON w.id = dl.worker_id
           JOIN products p ON p.id = dl.product_id
           WHERE dl.entry_date BETWEEN ? AND ? AND dl.status = 'present'
           GROUP BY dl.worker_id, p.code
           ORDER BY w.name, p.code""",
        (start, end),
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
            """INSERT INTO worker_monthly_history
               (worker_id, year, month, product_id, total_quantity, gross_amount)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(worker_id, year, month, product_id)
               DO UPDATE SET total_quantity = excluded.total_quantity,
                             gross_amount = excluded.gross_amount""",
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

    return {
        "status": "ok",
        "message": f"Backfilled {count} history records across {len(archived_months)} month(s)",
        "count": count,
        "months": [{"year": y, "month": m} for y, m in sorted(archived_months)],
    }


# ── Sessions ──────────────────────────────────────────

def create_session(session_id: str, email: str, is_admin: bool, ip_address: str = "", ttl_hours: int = 24):
    conn = get_db()
    from datetime import datetime, timedelta
    expires = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
    conn.execute(
        """INSERT INTO sessions (id, email, is_admin, ip_address, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, email, 1 if is_admin else 0, ip_address, expires),
    )
    conn.commit()


def get_session(session_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND revoked = 0 AND expires_at > datetime('now')",
        (session_id,),
    ).fetchone()
    return dict(row) if row else None


def revoke_session(session_id: str):
    conn = get_db()
    conn.execute("UPDATE sessions SET revoked = 1 WHERE id = ?", (session_id,))
    conn.commit()


def revoke_all_sessions_for_email(email: str):
    conn = get_db()
    conn.execute("UPDATE sessions SET revoked = 1 WHERE email = ? AND revoked = 0", (email,))
    conn.commit()


def cleanup_expired_sessions():
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")
    conn.commit()


# ── Auth Log ──────────────────────────────────────────

def log_auth_event(email: str, action: str, ip_address: str = "", details: str = ""):
    conn = get_db()
    conn.execute(
        "INSERT INTO auth_log (email, action, ip_address, details) VALUES (?, ?, ?, ?)",
        (email, action, ip_address, details),
    )
    conn.commit()


def get_recent_auth_logs(limit: int = 50) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM auth_log ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── OAuth States (DB-backed) ──────────────────────────

def save_oauth_state(state: str, code_verifier: str, redirect_uri: str):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO oauth_states (state, code_verifier, redirect_uri) VALUES (?, ?, ?)",
        (state, code_verifier, redirect_uri),
    )
    conn.commit()


def pop_oauth_state(state: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM oauth_states WHERE state = ?",
        (state,),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
        return dict(row)
    return None


def cleanup_expired_oauth_states(minutes: int = 10):
    conn = get_db()
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    conn.execute("DELETE FROM oauth_states WHERE created_at < ?", (cutoff,))
    conn.commit()
