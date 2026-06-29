from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.schemas import (
    StatusOut, HealthOut, WorkerMonthData, ArchiveCheckOut,
)
from api.routes.common import _check_auto_archive
from services.database import (
    get_all_workers, get_all_products,
    get_worker_id, get_worker_daily_breakdown,
    is_month_archived, get_all_history_months,
)
from services.export_tools import generate_worker_excel_stream

public_router = APIRouter()


@public_router.get("/", response_model=StatusOut)
async def worker_dashboard(background_tasks: BackgroundTasks) -> StatusOut:
    today = date.today()
    if today.day == 1:
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        if not is_month_archived(prev_year, prev_month):
            background_tasks.add_task(_check_auto_archive)
    return StatusOut(status="ok", message="Admin Ops AI is running")


@public_router.get("/api/health", response_model=HealthOut)
async def health_check() -> HealthOut:
    from services.database import get_db
    try:
        conn = get_db()
        workers = conn.execute("SELECT COUNT(*) as c FROM workers").fetchone()
        products = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()
        return HealthOut(
            status="ok",
            database="connected",
            workers_count=workers["c"] if workers else 0,
            products_count=products["c"] if products else 0,
        )
    except Exception as e:
        return HealthOut(status="error", database=str(e))


@public_router.get("/api/workers")
async def api_workers() -> dict:
    workers = get_all_workers()
    return {"workers": [{"id": w["id"], "name": w["name"]} for w in workers]}


@public_router.get("/api/products")
async def api_products() -> dict:
    products = get_all_products()
    return {"products": [{"id": p["id"], "code": p["code"]} for p in products]}


@public_router.get("/api/worker/{worker_name}/month/{year}/{month}", response_model=WorkerMonthData)
async def api_worker_month(worker_name: str, year: int, month: int) -> WorkerMonthData:
    wid = get_worker_id(worker_name)
    if not wid:
        raise HTTPException(404, f"Worker '{worker_name}' not found")
    if month < 1 or month > 12:
        raise HTTPException(400, "Invalid month")

    today = date.today()
    is_current = (year == today.year and month == today.month)

    days = get_worker_daily_breakdown(wid, year, month)
    has_any = any(d["status"] == "present" for d in days)

    if is_current:
        source = "live"
    elif is_month_archived(year, month) and has_any:
        source = "archived"
    else:
        source = "none" if not has_any else "live"

    return WorkerMonthData(worker=worker_name, year=year, month=month, days=days, source=source)


@public_router.get("/api/worker/{worker_name}/excel/{year}/{month}")
async def api_worker_excel(worker_name: str, year: int, month: int):
    wid = get_worker_id(worker_name)
    if not wid:
        raise HTTPException(404, f"Worker '{worker_name}' not found")
    if month < 1 or month > 12:
        raise HTTPException(400, "Invalid month")

    result = generate_worker_excel_stream(worker_name, year, month)
    if not result:
        raise HTTPException(404, "No data for this worker and month")
    buf, filename = result
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@public_router.get("/api/archive/check", response_model=ArchiveCheckOut)
async def api_archive_check() -> ArchiveCheckOut:
    today = date.today()
    prev_month = today.month - 1 or 12
    prev_year = today.year if today.month > 1 else today.year - 1
    return ArchiveCheckOut(
        is_first_day=today.day == 1,
        prev_month_archived=is_month_archived(prev_year, prev_month),
        prev_month={"year": prev_year, "month": prev_month},
    )


@public_router.get("/api/history/months")
async def api_history_months() -> dict:
    return {"months": get_all_history_months()}
