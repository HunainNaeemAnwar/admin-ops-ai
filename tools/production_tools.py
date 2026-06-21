import json
import sqlite3
from datetime import date
from typing import Optional

from config import TAX_PERCENTAGE
from tools.database import (
    get_db, get_worker_id, get_or_create_worker,
    log_production as db_log, mark_absent as db_mark_absent,
    update_entry as db_update, ensure_day_complete,
    get_all_products, get_active_workers,
)


VALID_PRODUCTS = {"NUT", "10*20", "6*25", "6*30", "10*25"}


def get_product_info(code: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
    conn.close()
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


def _record_single(worker: str, product_code: str, quantity: int) -> str:
    result = calc_piece_rate(product_code, quantity)
    if "error" in result:
        return f"  {worker}: {result['error']}"
    try:
        worker_id = get_or_create_worker(worker)
        product_id = get_product_info(product_code)["id"]
        today = date.today().isoformat()
        db_log(worker_id, product_id, quantity, today)
        return f"  {worker}: {quantity}x{product_code}"
    except sqlite3.IntegrityError:
        worker_id = get_worker_id(worker)
        product_id = get_product_info(product_code)["id"]
        today = date.today().isoformat()
        conn = get_db()
        row = conn.execute(
            "SELECT id FROM daily_log WHERE worker_id = ? AND product_id = ? AND entry_date = ?",
            (worker_id, product_id, today),
        ).fetchone()
        conn.close()
        if row:
            db_update(row["id"], quantity)
            return f"  {worker}: {quantity}x{product_code} (updated)"
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
        worker = entry.get("worker", "")
        product_code = entry.get("product_code", "")
        quantity = entry.get("quantity", 0)
        if not worker or not product_code or quantity <= 0:
            results.append(f"  Invalid: {entry}")
            continue
        results.append(_record_single(worker, product_code, quantity))

    if not results:
        return "No valid entries"

    return "\n".join(results)


def mark_absent(worker: str, entry_date: Optional[str] = None) -> str:
    if entry_date is None:
        entry_date = date.today().isoformat()
    worker_id = get_or_create_worker(worker)
    try:
        db_mark_absent(worker_id, entry_date)
        return f"Marked {worker} absent for {entry_date}"
    except sqlite3.IntegrityError:
        return f"{worker} already has an entry for {entry_date}"


def mark_all_absent(entry_date: Optional[str] = None) -> str:
    if entry_date is None:
        entry_date = date.today().isoformat()
    workers = get_active_workers()
    results = []
    for w in workers:
        try:
            db_mark_absent(w["id"], entry_date)
            results.append(w["name"])
        except sqlite3.IntegrityError:
            pass
    if results:
        return f"Marked absent: {', '.join(results)}"
    return "All workers already have entries for today"


def update_entry(entry_id: int, new_quantity: int, reason: str = "") -> str:
    conn = get_db()
    row = conn.execute("SELECT * FROM daily_log WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    if not row:
        return f"Entry {entry_id} not found"

    old_qty = row["quantity"]
    db_update(entry_id, new_quantity)
    msg = f"Entry {entry_id}: {old_qty} -> {new_quantity}"
    if reason:
        msg += f" ({reason})"
    return msg
