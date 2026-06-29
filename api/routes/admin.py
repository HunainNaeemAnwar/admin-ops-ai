from datetime import date
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from api.schemas import (
    DailyReport, DailyLogEntry, MonthlyReport, MonthlyWorkerSummary,
)
from api.routes.common import (
    CurrentUser, require_admin,
)
from config import PDF_DIR
from services.database import (
    get_all_workers, get_all_products, get_logs_for_date,
    get_daily_totals, get_worker_id, get_worker_month_production,
)
from services.export_tools import generate_monthly_excel_stream

admin_router = APIRouter()

@admin_router.get("/daily", response_model=DailyReport)
async def admin_daily_report(
    user: CurrentUser,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    day: Optional[int] = Query(None),
) -> DailyReport:
    require_admin(user)
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    date_str = f"{y}-{m:02d}-{d:02d}"
    logs = get_logs_for_date(date_str)
    totals = get_daily_totals(date_str)
    return DailyReport(
        date=date_str,
        entries=[DailyLogEntry(**dict(l)) for l in logs],
        totals=totals,
        total_pieces=sum(totals.values()),
    )

@admin_router.get("/monthly", response_model=MonthlyReport)
async def admin_monthly_report(
    user: CurrentUser,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
) -> MonthlyReport:
    require_admin(user)
    today = date.today()
    y = year or today.year
    m = month or today.month
    workers = get_all_workers()
    worker_data = []
    for w in workers:
        entries = get_worker_month_production(w["id"], y, m)
        worker_totals = {}
        for e in entries:
            code = e["product_code"]
            worker_totals[code] = worker_totals.get(code, 0) + e["quantity"]
        worker_data.append(MonthlyWorkerSummary(worker=w["name"], totals=worker_totals))
    return MonthlyReport(year=y, month=m, workers=worker_data)

@admin_router.get("/monthly/excel")
async def admin_monthly_excel(
    user: CurrentUser,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
):
    require_admin(user)
    today = date.today()
    y = year or today.year
    m = month or today.month
    buf, filename = generate_monthly_excel_stream(y, m)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@admin_router.get("/workers")
async def admin_workers_list(user: CurrentUser) -> dict:
    require_admin(user)
    workers = get_all_workers()
    return {"workers": [w["name"] for w in workers]}

@admin_router.get("/worker/{worker}")
async def admin_worker_detail(
    user: CurrentUser,
    worker: str,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
) -> dict:
    require_admin(user)
    today = date.today()
    y = year or today.year
    m = month or today.month
    wid = get_worker_id(worker)
    if not wid:
        raise HTTPException(404, f"Worker '{worker}' not found")
    entries = get_worker_month_production(wid, y, m)
    return {"worker": worker, "year": y, "month": m, "entries": entries}

@admin_router.get("/products")
async def admin_products(user: CurrentUser) -> dict:
    require_admin(user)
    return {"products": get_all_products()}

@admin_router.get("/payslips")
async def admin_list_payslips(user: CurrentUser, year: int = 0, month: int = 0) -> dict:
    require_admin(user)
    from config import PDF_DIR
    today = date.today()
    y = year or today.year
    m = month or today.month
    pdfs = []
    if PDF_DIR.exists():
        for f in sorted(PDF_DIR.glob(f"*_{y}_{m:02d}.pdf")):
            pdfs.append(f.stem)
    return {"year": y, "month": m, "pdfs": pdfs, "excels": []}

@admin_router.get("/payslip/pdf/{worker}/{year}/{month}")
async def admin_download_payslip_pdf(worker: str, year: int, month: int, user: CurrentUser) -> FileResponse:
    require_admin(user)
    from config import PDF_DIR
    filepath = PDF_DIR / f"{worker}_{year}_{month:02d}.pdf"
    if not filepath.exists():
        raise HTTPException(404, "Payslip not found")
    return FileResponse(
        str(filepath),
        filename=f"{worker}_{year}_{month:02d}.pdf",
        media_type="application/pdf",
    )
