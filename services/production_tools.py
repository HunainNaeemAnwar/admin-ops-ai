import asyncio
import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from config import TAX_PERCENTAGE
from services.database import (
    get_db, get_worker_id, get_or_create_worker,
    log_production as db_log, mark_absent as db_mark_absent,
    update_entry as db_update,
    get_all_products, get_active_workers,
)


class OverwriteTracker:
    """Async-safe overwrite confirmation tracker.

    Workers confirm overwrites by sending the same command twice.
    Stores pending confirmations with TTL expiry.
    """

    def __init__(self, ttl_seconds: int = 300):
        self._lock = asyncio.Lock()
        self._data: dict[tuple[str, str, str], bool] = {}
        self._ts: dict[tuple[str, str, str], datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    async def check(self, key: tuple[str, str, str]) -> bool:
        async with self._lock:
            self._evict()
            if key in self._data and self._data[key]:
                del self._data[key]
                del self._ts[key]
                return True
            self._data[key] = True
            self._ts[key] = datetime.now()
            return False

    def _evict(self):
        cutoff = datetime.now() - self._ttl
        stale = [k for k, t in self._ts.items() if t < cutoff]
        for k in stale:
            del self._data[k]
            del self._ts[k]


_pending_overwrites = OverwriteTracker()


class ProductionInput:
    """Validated production entry input."""
    def __init__(self, worker: str, product_code: str, quantity: int, entry_date: str = ""):
        if product_code not in VALID_PRODUCTS:
            raise ValueError(f"Invalid product '{product_code}'. Valid: {', '.join(sorted(VALID_PRODUCTS))}")
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        if entry_date:
            try:
                datetime.strptime(entry_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {entry_date}. Use YYYY-MM-DD")
        self.worker = worker
        self.product_code = product_code
        self.quantity = quantity
        self.entry_date = entry_date or date.today().isoformat()

    def to_dict(self) -> dict:
        return {"worker": self.worker, "product_code": self.product_code, "quantity": self.quantity, "date": self.entry_date}

VALID_PRODUCTS = {"NUT", "10*20", "6*25", "6*30", "10*25"}

def get_product_info(code: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
    return dict(row) if row else None


def calc_piece_rate(product_code: str, quantity: int) -> dict:
    product = get_product_info(product_code)
    if not product:
        return {"error": f"Unknown product '{product_code}'. Valid: {', '.join(sorted(VALID_PRODUCTS))}"}
    rate = product["rate"]
    tax_pct = product["tax_pct"] if product["tax_pct"] > 0 else TAX_PERCENTAGE
    gross = round(quantity * rate, 2)
    tax_amt = round(gross * tax_pct / 100, 2)
    net = round(gross - tax_amt, 2)
    return {
        "product_code": product["code"],
        "description": product["description"],
        "rate": rate,
        "quantity": quantity,
        "gross": gross,
        "tax_pct": tax_pct,
        "tax_amt": tax_amt,
        "net": net,
    }


def _record_single(worker: str, product_code: str, quantity: int, entry_date: Optional[str] = None) -> str:
    result = calc_piece_rate(product_code, quantity)
    if "error" in result:
        return f"  {worker}: {result['error']}"
    if entry_date is None:
        entry_date = date.today().isoformat()
    worker_id = get_or_create_worker(worker)
    product_id = get_product_info(product_code)["id"]
    try:
        db_log(worker_id, product_id, quantity, entry_date)
        return f"  {worker}: {quantity}x{product_code}"
    except sqlite3.IntegrityError:
        conn = get_db()
        row = conn.execute(
            "SELECT id, quantity FROM daily_log WHERE worker_id = ? AND product_id = ? AND entry_date = ?",
            (worker_id, product_id, entry_date),
        ).fetchone()
        if row:
            return f"  {worker}: Already has {row['quantity']}x{product_code} for {entry_date}. Use update_entry to change."
        return f"  {worker}: Already exists"


def log_production_json(json_str: str) -> str:
    try:
        entries = json.loads(json_str)
        if isinstance(entries, dict):
            entries = [entries]
    except (json.JSONDecodeError, TypeError):
        return "Invalid JSON format. Use: [{\"worker\":\"Kaleem\",\"product_code\":\"NUT\",\"quantity\":300}]"

    if not isinstance(entries, list):
        return "Must be a JSON array"

    results = []
    for entry in entries:
        if not isinstance(entry, dict):
            results.append(f"  Invalid entry (must be object): {entry}")
            continue
        worker = entry.get("worker", "")
        product_code = entry.get("product_code", "")
        quantity = entry.get("quantity", 0)
        entry_date = entry.get("date", None)
        if entry_date is None:
            entry_date = date.today().isoformat()
        if not worker or not product_code or quantity <= 0:
            results.append(f"  Invalid: {entry}")
            continue
        results.append(_record_single(worker, product_code, quantity, entry_date))

    if not results:
        return "No valid entries"

    return "\n".join(results)


def mark_absent(worker: str, entry_date: Optional[str] = None, reason: str = "") -> str:
    if entry_date is None:
        entry_date = date.today().isoformat()
    worker_id = get_or_create_worker(worker)
    db_mark_absent(worker_id, entry_date, reason)
    msg = f"Marked {worker} absent for {entry_date}"
    if reason:
        msg += f" ({reason})"
    return msg


def mark_all_absent(entry_date: Optional[str] = None, reason: str = "") -> str:
    if entry_date is None:
        entry_date = date.today().isoformat()
    workers = get_active_workers()
    results = []
    for w in workers:
        db_mark_absent(w["id"], entry_date, reason)
        results.append(w["name"])
    if results:
        msg = f"Marked absent: {', '.join(results)}"
        if reason:
            msg += f" ({reason})"
        return msg
    return "All workers already have entries for today"


def update_entry(entry_id: int, new_quantity: int, reason: str = "") -> str:
    if new_quantity < 0:
        return f"Quantity cannot be negative"
    row = get_db().execute("SELECT * FROM daily_log WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        return f"Entry {entry_id} not found"

    old_qty = row["quantity"]
    db_update(entry_id, new_quantity)
    msg = f"Entry {entry_id}: {old_qty} -> {new_quantity}"
    if reason:
        msg += f" ({reason})"
    return msg


async def record_production(worker: str, product_code: str, quantity: int, entry_date: str = "") -> str:
    inp = ProductionInput(worker, product_code, quantity, entry_date)
    result = calc_piece_rate(inp.product_code, inp.quantity)
    if "error" in result:
        return f"  {inp.worker}: {result['error']}"

    worker_id = get_or_create_worker(inp.worker)
    product_id = get_product_info(inp.product_code)["id"]
    try:
        db_log(worker_id, product_id, inp.quantity, inp.entry_date)
        return f"  {inp.worker}: {inp.quantity}x{inp.product_code}"
    except sqlite3.IntegrityError:
        conn = get_db()
        row = conn.execute(
            "SELECT id, quantity FROM daily_log WHERE worker_id = ? AND product_id = ? AND entry_date = ?",
            (worker_id, product_id, inp.entry_date),
        ).fetchone()
        if row:
            key = (inp.worker, inp.product_code, inp.entry_date)
            confirmed = await _pending_overwrites.check(key)
            if confirmed:
                db_update(row["id"], inp.quantity)
                return f"  {inp.worker}: {inp.quantity}x{inp.product_code} (overwritten, was {row['quantity']})"
            return (
                f"  ⚠️ {inp.worker} already has {row['quantity']}x{inp.product_code} for {inp.entry_date}.\n"
                f"     Send same command again to overwrite."
            )
        return f"  {inp.worker}: Already exists"


async def record_production_batch(entries: list[dict]) -> str:
    results = []
    for entry in entries:
        if not isinstance(entry, dict):
            results.append(f"  Invalid entry: {entry}")
            continue
        worker = entry.get("worker", "")
        product_code = entry.get("product_code", "")
        quantity = entry.get("quantity", 0)
        entry_date = entry.get("date", "")
        if not worker or not product_code or quantity <= 0:
            results.append(f"  Invalid: {entry}")
            continue
        result = await record_production(worker, product_code, quantity, entry_date)
        results.append(result)
    return "\n".join(results) if results else "No valid entries"


PRODUCT_COLUMNS = {"NUT", "6*30", "6*25", "10*20", "10*25"}
CODE_ALIASES = {
    "6×30": "6*30", "6x30": "6*30", "6X30": "6*30",
    "6×25": "6*25", "6x25": "6*25", "6X25": "6*25",
    "10×20": "10*20", "10x20": "10*20", "10X20": "10*20",
    "10×25": "10*25", "10x25": "10*25", "10X25": "10*25",
}


def _normalize_code(code: str) -> str:
    return CODE_ALIASES.get(code, code)


def _parse_date(date_str: str) -> Optional[str]:
    date_str = date_str.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_table_to_production(worker: str, table_text: str) -> str:
    import re
    lines = table_text.strip().split("\n")
    header_line = None
    data_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "│":
            continue
        if re.search(r'DATE|NUT|6[×xX*]30|6[×xX*]25|10[×xX*]20|10[×xX*]25', stripped, re.IGNORECASE):
            header_line = stripped
            in_table = True
            continue
        if re.match(r'[└┴┘]+', stripped):
            in_table = False
            continue
        if in_table:
            if re.match(r'[├┼┤┬┌┐─═\s]+$', stripped):
                continue
            parts = [p.strip() for p in stripped.split("│")]
            if len(parts) >= 2:
                data_lines.append(parts)

    if not header_line or not data_lines:
        return "Could not parse table — no header or data rows found."

    header_parts = [p.strip() for p in header_line.split("│")]
    col_map = {}
    for i, h in enumerate(header_parts):
        h_upper = h.upper().replace("*", "").replace("×", "").replace("X", "")
        if h_upper == "DATE":
            col_map[i] = "date"
        elif _normalize_code(h) in PRODUCT_COLUMNS:
            col_map[i] = _normalize_code(h)

    product_cols = {i: code for i, code in col_map.items() if code != "date"}
    date_col = next((i for i, v in col_map.items() if v == "date"), None)
    if date_col is None:
        return "Could not find DATE column in table."

    wid = get_or_create_worker(worker)
    results = []
    for row_parts in data_lines:
        if len(row_parts) <= max(col_map.keys()):
            continue
        raw_date = row_parts[date_col].strip()
        iso_date = _parse_date(raw_date)
        if not iso_date:
            results.append(f"  Skipped {raw_date}: bad date")
            continue

        has_data = False
        date_results = []
        for col_idx, product_code in product_cols.items():
            try:
                qty = int(row_parts[col_idx].strip().replace(",", ""))
            except (ValueError, IndexError):
                continue
            if qty <= 0:
                continue
            has_data = True
            pid = get_product_info(product_code)
            if not pid:
                continue
            try:
                db_log(wid, pid["id"], qty, iso_date)
            except sqlite3.IntegrityError:
                existing = get_db().execute(
                    "SELECT id, quantity FROM daily_log WHERE worker_id = ? AND product_id = ? AND entry_date = ?",
                    (wid, pid["id"], iso_date),
                ).fetchone()
                if existing:
                    date_results.append(f"{qty}x{product_code} (exists, skipped)")
                else:
                    date_results.append(f"{qty}x{product_code} (skipped)")
                continue
            date_results.append(f"{qty}x{product_code}")

        if has_data:
            results.append(f"  {iso_date}: {', '.join(date_results)}")
        else:
            results.append(f"  {iso_date}: no data")

    if not results:
        return "No valid data found in table."
    return "\n".join(results)
