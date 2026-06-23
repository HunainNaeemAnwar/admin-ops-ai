"""Tool Bus — Layer 3 in the 4-Layer Architecture.

Provides a validated, deterministic interface between agents (Layer 1-2)
and data adapters (Layer 4). Handles input validation, error coordination,
and consistent response formatting.

Usage: orchestrator.py imports from here instead of individual tool modules.
"""

import json
import sqlite3
import time
from datetime import date
from typing import Optional

from tools.database import (
    get_db, get_worker_id, get_or_create_worker,
    get_active_workers, get_all_products,
    get_logs_for_date, get_daily_totals,
    get_worker_month_production,
    get_product_id, get_product_rate,
    get_total_advances_for_worker_month,
    save_payslip,
    log_production as db_log_production,
    mark_absent as db_mark_absent,
    update_entry as db_update_entry,
    log_rejection as db_log_rejection,
    get_rejections_for_month,
    record_advance as db_record_advance,
)
from tools.production_tools import (
    get_product_info, calc_piece_rate, parse_table_to_production,
)


VALID_PRODUCTS = {"NUT", "10*20", "6*25", "6*30", "10*25"}
_pending_overwrites: dict[tuple[str, str, str], bool] = {}
_pending_overwrites_ts: float = time.time()


def _clean_stale_overwrites():
    global _pending_overwrites_ts
    now = time.time()
    if now - _pending_overwrites_ts > 300:
        _pending_overwrites.clear()
        _pending_overwrites_ts = now


# ── Production ───────────────────────────────────────

class ProductionInput:
    """Validated production entry input."""
    def __init__(self, worker: str, product_code: str, quantity: int, entry_date: str = ""):
        if product_code not in VALID_PRODUCTS:
            raise ValueError(f"Invalid product '{product_code}'. Valid: {', '.join(sorted(VALID_PRODUCTS))}")
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        if entry_date and len(entry_date) != 10:
            raise ValueError(f"Invalid date format: {entry_date}")
        self.worker = worker
        self.product_code = product_code
        self.quantity = quantity
        self.entry_date = entry_date or date.today().isoformat()

    def to_dict(self) -> dict:
        return {"worker": self.worker, "product_code": self.product_code, "quantity": self.quantity, "date": self.entry_date}


def record_production(worker: str, product_code: str, quantity: int, entry_date: str = "") -> str:
    _clean_stale_overwrites()
    inp = ProductionInput(worker, product_code, quantity, entry_date)
    result = calc_piece_rate(inp.product_code, inp.quantity)
    if "error" in result:
        return f"  {inp.worker}: {result['error']}"

    worker_id = get_or_create_worker(inp.worker)
    product_id = get_product_info(inp.product_code)["id"]
    try:
        db_log_production(worker_id, product_id, inp.quantity, inp.entry_date)
        return f"  {inp.worker}: {inp.quantity}x{inp.product_code}"
    except sqlite3.IntegrityError:
        conn = get_db()
        row = conn.execute(
            "SELECT id, quantity FROM daily_log WHERE worker_id = ? AND product_id = ? AND entry_date = ?",
            (worker_id, product_id, inp.entry_date),
        ).fetchone()
        if row:
            key = (inp.worker, inp.product_code, inp.entry_date)
            if key in _pending_overwrites and _pending_overwrites[key]:
                del _pending_overwrites[key]
                db_update_entry(row["id"], inp.quantity)
                return f"  {inp.worker}: {inp.quantity}x{inp.product_code} (overwritten, was {row['quantity']})"
            _pending_overwrites[key] = True
            return (
                f"  ⚠️ {inp.worker} already has {row['quantity']}x{inp.product_code} for {inp.entry_date}.\n"
                f"     Send same command again to overwrite."
            )
        return f"  {inp.worker}: Already exists"


def record_production_batch(entries: list[dict]) -> str:
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
        results.append(record_production(worker, product_code, quantity, entry_date))
    return "\n".join(results) if results else "No valid entries"


def mark_worker_absent(worker: str, entry_date: str = "", reason: str = "") -> str:
    entry_date = entry_date or date.today().isoformat()
    worker_id = get_or_create_worker(worker)
    try:
        db_mark_absent(worker_id, entry_date, reason)
        msg = f"Marked {worker} absent for {entry_date}"
        if reason:
            msg += f" ({reason})"
        return msg
    except sqlite3.IntegrityError:
        return f"{worker} already has an entry for {entry_date}"


def mark_all_workers_absent(entry_date: str = "", reason: str = "") -> str:
    entry_date = entry_date or date.today().isoformat()
    workers = get_active_workers()
    results = []
    for w in workers:
        try:
            db_mark_absent(w["id"], entry_date, reason)
            results.append(w["name"])
        except sqlite3.IntegrityError:
            pass
    if results:
        msg = f"Marked absent: {', '.join(results)}"
        if reason:
            msg += f" ({reason})"
        return msg
    return "All workers already have entries for today"


def update_production_entry(entry_id: int, new_quantity: int, reason: str = "") -> str:
    if new_quantity < 0:
        return "Quantity cannot be negative"
    row = get_db().execute("SELECT * FROM daily_log WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        return f"Entry {entry_id} not found"
    old_qty = row["quantity"]
    db_update_entry(entry_id, new_quantity)
    msg = f"Entry {entry_id}: {old_qty} -> {new_quantity}"
    if reason:
        msg += f" ({reason})"
    return msg


def parse_table(worker: str, table_text: str) -> str:
    return parse_table_to_production(worker, table_text)


# ── Reporting ────────────────────────────────────────

def get_date_status(date_str: str = "") -> str:
    date_str = date_str or date.today().isoformat()
    from tools.report_tools import get_daily_status
    return get_daily_status(date_str)


def get_production_summary(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    from tools.report_tools import get_summary
    today = date.today()
    return get_summary(period, year or today.year, month or today.month, day or today.day)


def get_catalog() -> str:
    today = date.today()
    workers = get_active_workers()
    products = get_all_products()
    lines = [
        f"Today: {today.isoformat()}",
        f"",
        f"Workers ({len(workers)}):",
    ]
    for w in workers:
        lines.append(f"  {w['name']}")
    lines.append(f"\nProducts:")
    for p in products:
        lines.append(f"  {p['code']}: Rs {p['rate']:,.2f}/pc ({p['description']})")
    status = get_date_status()
    lines.append(f"\nToday's Status:")
    lines.append(f"  {status}")
    return "\n".join(lines)


# ── Rejection ────────────────────────────────────────

def record_rejection(year: int, month: int, product_code: str, total_qty: int, excluded_workers: Optional[list[str]] = None) -> str:
    product = get_product_info(product_code)
    if not product:
        return f"Unknown product '{product_code}'. Valid: NUT, 10*20, 6*25, 6*30, 10*25"
    if excluded_workers is None:
        excluded_workers = []
    rid = db_log_rejection(year, month, product["id"], total_qty, excluded_workers)
    active = get_active_workers()
    eligible = [w["name"] for w in active if w["name"] not in excluded_workers]
    if not eligible:
        return f"Rejection recorded (id={rid}). No eligible workers for distribution."
    base = total_qty // len(eligible)
    remainder = total_qty % len(eligible)
    lines = [
        f"Rejection recorded (id={rid}): {total_qty}x{product_code} for {year}-{month:02d}",
        f"Eligible workers ({len(eligible)}): {', '.join(eligible)}",
        f"Distribution: {base} each",
    ]
    if remainder:
        extra = eligible[:remainder]
        lines.append(f"Extra 1 piece to: {', '.join(extra)}")
    if excluded_workers:
        lines.append(f"Excluded: {', '.join(excluded_workers)}")
    return "\n".join(lines)


def get_rejection_distribution(year: int, month: int) -> list[dict]:
    return get_rejections_for_month(year, month)


# ── Advances ─────────────────────────────────────────

def record_worker_advance(worker: str, amount: float, year: int, month: int, description: str = "") -> str:
    worker_id = get_or_create_worker(worker)
    aid = db_record_advance(worker_id, amount, year, month, description)
    total = get_total_advances_for_worker_month(worker_id, year, month)
    return (
        f"Advance recorded (id={aid}): Rs {amount:,.2f} for {worker} ({year}-{month:02d})\n"
        f"Total advances for {worker} this month: Rs {total:,.2f}"
    )


# ── Payslip ─────────────────────────────────────────

def generate_worker_payslip(worker: str, year: int, month: int) -> dict | None:
    wid = get_worker_id(worker)
    if not wid:
        return None
    from tools.payslip_tools import _build_payslip_data
    return _build_payslip_data(worker, year, month)


def generate_payslip_files(worker: str, year: int, month: int) -> tuple[str, str]:
    from tools.payslip_tools import generate_pdf_payslip, generate_excel_payslip
    pdf = generate_pdf_payslip(worker, year, month)
    xls = generate_excel_payslip(worker, year, month)
    return pdf, xls
