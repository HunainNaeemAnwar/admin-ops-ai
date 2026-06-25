import json
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Request, HTTPException, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, StreamingResponse

from config import BASE_DIR, FRONTEND_URL
from schemas import (
    WorkerOut, ProductOut, DailyReport, DailyLogEntry, WorkerMonthData,
    WorkerDailyBreakdown, MonthlyReport, MonthlyWorkerSummary,
    AuthUserOut, ArchiveCheckOut, StatusOut,
    RecordWorkIn, RejectionIn, AdvanceIn, PayslipIn, EmailReportIn,
    ChatIn, ChatOut, ActionOut, HealthOut,
)
from tools.oauth_tools import (
    _get_fernet, get_authorization_url, exchange_code, save_token,
    list_authorized_users, delete_token, is_father_email,
)
from tools.database import (
    get_all_workers, get_all_products, get_logs_for_date,
    get_worker_id, get_worker_month_production, get_daily_totals,
    get_worker_daily_breakdown, is_month_archived,
    get_all_history_months,
)
from tools.production_tools import log_production_json
from tools.export_tools import generate_worker_excel

router = APIRouter()
admin_router = APIRouter(prefix="/admin")

TEMPLATES_DIR = BASE_DIR / "web_ui" / "templates"
_oauth_states: dict[str, dict] = {}


def _read_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def _base_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host", request.url.hostname)
    port = request.url.port
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _render(template_name: str, **kwargs) -> str:
    html = _read_template(template_name)
    for key, val in kwargs.items():
        placeholder = "{{ " + key + " }}"
        if isinstance(val, list):
            html = html.replace(placeholder, "\n".join(str(v) for v in val))
        elif isinstance(val, dict):
            html = html.replace(placeholder, str(val))
        else:
            html = html.replace(placeholder, str(val) if val is not None else "")

    users = kwargs.get("users", [])
    if "users" in kwargs:
        if users:
            email = users[0]
            father_tag = " ⭐" if is_father_email(email) else ""
            html = html.replace(
                "<!--USERS-->",
                f'<span style="opacity:0.9;">{email}{father_tag}</span>'
                f'<a href="/admin/logout?email={email}" style="color:#ffd700;">Logout</a>'
            )
        else:
            html = html.replace(
                "<!--USERS-->",
                '<a href="/admin/login" class="login-btn">Sign in with Google</a>'
            )
    return html


def _decrypt_auth_cookie(request: Request) -> str | None:
    auth_cookie = request.cookies.get("auth")
    if not auth_cookie:
        return None
    try:
        fernet = _get_fernet()
        raw = fernet.decrypt(auth_cookie.encode())
        data = json.loads(raw.decode())
        return data.get("email", "")
    except Exception:
        return None


def get_current_user(request: Request) -> str | None:
    email = _decrypt_auth_cookie(request)
    if email:
        return email
    users = list_authorized_users()
    return users[0] if users else None


CurrentUser = Annotated[str | None, Depends(get_current_user)]


def require_father(user: str | None):
    if not user or not is_father_email(user):
        raise HTTPException(403, "Only father can perform this action")


def require_auth(user: str | None):
    if not user:
        raise HTTPException(401, "Authentication required")


def _check_auto_archive():
    today = date.today()
    if today.day != 1:
        return
    prev_month = today.month - 1 or 12
    prev_year = today.year if today.month > 1 else today.year - 1
    if is_month_archived(prev_year, prev_month):
        return
    from tools.database import get_active_workers, get_all_products, insert_worker_history
    workers = get_active_workers()
    products = get_all_products()
    for w in workers:
        breakdown = get_worker_daily_breakdown(w["id"], prev_year, prev_month)
        if not breakdown:
            continue
        product_totals = {}
        for day in breakdown:
            if day["status"] == "present":
                for code, qty in day["products"].items():
                    product_totals[code] = product_totals.get(code, 0) + qty
        for p in products:
            qty = product_totals.get(p["code"], 0)
            if qty > 0:
                gross = qty * p["rate"]
                insert_worker_history(w["id"], prev_year, prev_month, p["id"], qty, gross)
        generate_worker_excel(w["name"], prev_year, prev_month)


# ── AUTH ROUTES ──────────────────────────────────────

@router.get("/api/auth/me", response_model=AuthUserOut)
async def api_auth_me(request: Request) -> AuthUserOut:
    auth_cookie = request.cookies.get("auth")
    if not auth_cookie:
        return AuthUserOut()
    try:
        fernet = _get_fernet()
        raw = fernet.decrypt(auth_cookie.encode())
        data = json.loads(raw.decode())
        return AuthUserOut(
            email=data.get("email", ""),
            is_father=data.get("is_father", False),
            authenticated=True,
        )
    except Exception:
        return AuthUserOut()


@router.post("/api/auth/logout")
async def api_auth_logout() -> JSONResponse:
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie("auth", path="/")
    return resp


# ── PUBLIC ROUTES ────────────────────────────────────

@router.get("/", response_model=StatusOut)
async def worker_dashboard() -> StatusOut:
    _check_auto_archive()
    return StatusOut(status="ok", message="Admin Ops AI is running")


@router.get("/api/health", response_model=HealthOut)
async def health_check() -> HealthOut:
    from tools.database import get_db
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


@router.get("/api/workers")
async def api_workers() -> dict:
    workers = get_all_workers()
    return {"workers": [{"id": w["id"], "name": w["name"]} for w in workers]}


@router.get("/api/products")
async def api_products() -> dict:
    products = get_all_products()
    return {"products": [{"id": p["id"], "code": p["code"]} for p in products]}


@router.get("/api/worker/{worker_name}/month/{year}/{month}", response_model=WorkerMonthData)
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


@router.get("/api/worker/{worker_name}/excel/{year}/{month}")
async def api_worker_excel(worker_name: str, year: int, month: int) -> FileResponse:
    wid = get_worker_id(worker_name)
    if not wid:
        raise HTTPException(404, f"Worker '{worker_name}' not found")
    if month < 1 or month > 12:
        raise HTTPException(400, "Invalid month")

    filepath = generate_worker_excel(worker_name, year, month)
    if not filepath:
        raise HTTPException(404, "No data for this worker and month")
    return FileResponse(
        filepath,
        filename=f"{worker_name}_{year}_{month:02d}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/api/archive/check", response_model=ArchiveCheckOut)
async def api_archive_check() -> ArchiveCheckOut:
    today = date.today()
    prev_month = today.month - 1 or 12
    prev_year = today.year if today.month > 1 else today.year - 1
    return ArchiveCheckOut(
        is_first_day=today.day == 1,
        prev_month_archived=is_month_archived(prev_year, prev_month),
        prev_month={"year": prev_year, "month": prev_month},
    )


@router.get("/api/history/months")
async def api_history_months() -> dict:
    return {"months": get_all_history_months()}


# ── OAUTH ROUTES ─────────────────────────────────────

@admin_router.get("/login")
async def admin_login(request: Request) -> RedirectResponse:
    base = _base_url(request)
    redirect_uri = f"{base}/oauth/callback"
    auth_url, state, code_verifier = get_authorization_url(redirect_uri)
    _oauth_states[state] = {
        "created": datetime.now().isoformat(),
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    return RedirectResponse(auth_url)


@router.get("/oauth/callback", response_model=None)
async def oauth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
):
    if error:
        return HTMLResponse(f"<h2>Error: {error}</h2><a href='/admin'>Go back</a>", status_code=400)
    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    state_data = _oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(400, "Invalid state parameter")

    redirect_uri = state_data["redirect_uri"]
    code_verifier = state_data.get("code_verifier", "")
    full_url = str(request.url)
    creds, email = exchange_code(state, redirect_uri, full_url, code_verifier)
    save_token(email, creds)

    is_father = is_father_email(email)
    cookie_data = json.dumps({"email": email, "is_father": is_father})
    fernet = _get_fernet()
    encrypted = fernet.encrypt(cookie_data.encode()).decode()

    redirect_path = f"{FRONTEND_URL}/admin" if is_father else f"{FRONTEND_URL}/"
    resp = RedirectResponse(url=redirect_path, status_code=303)
    resp.set_cookie(
        key="auth",
        value=encrypted,
        max_age=259200,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return resp


@admin_router.get("/logout")
async def admin_logout(email: str = None) -> RedirectResponse:
    if email:
        delete_token(email)
    return RedirectResponse(url="/admin")


# ── ADMIN ROUTES ─────────────────────────────────────

@admin_router.get("", response_class=HTMLResponse)
@admin_router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request, user: CurrentUser) -> str:
    require_auth(user)
    users = list_authorized_users()
    today = date.today()

    logs = get_logs_for_date(today.isoformat())
    present = set(l["worker_name"] for l in logs if l["status"] == "present")
    totals = get_daily_totals(today.isoformat())

    products = get_all_products()
    rate_map = {p["code"]: p["rate"] for p in products}
    daily_value = sum(totals.get(code, 0) * rate_map.get(code, 0) for code in totals)

    return _render(
        "index.html",
        today=today.isoformat(),
        users=users,
        daily_total=f"Rs {daily_value:,.2f}",
        daily_workers=str(len(present)),
        daily_pieces=str(sum(totals.values())),
        daily_entries=str(len(logs)),
        daily_workers_list=", ".join(sorted(present)) or "None",
    )


@admin_router.get("/daily", response_model=DailyReport)
async def admin_daily_report(
    user: CurrentUser,
    year: Annotated[Optional[int], Query()] = None,
    month: Annotated[Optional[int], Query()] = None,
    day: Annotated[Optional[int], Query()] = None,
) -> DailyReport:
    require_auth(user)
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
    year: Annotated[Optional[int], Query()] = None,
    month: Annotated[Optional[int], Query()] = None,
) -> MonthlyReport:
    require_auth(user)
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
    year: Annotated[Optional[int], Query()] = None,
    month: Annotated[Optional[int], Query()] = None,
) -> FileResponse:
    require_auth(user)
    from tools.export_tools import generate_excel_report
    today = date.today()
    y = year or today.year
    m = month or today.month
    filepath = generate_excel_report(period="monthly", year=y, month=m)
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"report_monthly_{y}-{m:02d}.xlsx",
    )


@admin_router.get("/workers")
async def admin_workers_list(user: CurrentUser) -> dict:
    require_auth(user)
    workers = get_all_workers()
    return {"workers": [w["name"] for w in workers]}


@admin_router.get("/worker/{worker}")
async def admin_worker_detail(
    user: CurrentUser,
    worker: str,
    year: Annotated[Optional[int], Query()] = None,
    month: Annotated[Optional[int], Query()] = None,
) -> dict:
    require_auth(user)
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
    require_auth(user)
    return {"products": get_all_products()}


@admin_router.post("/record", response_model=ActionOut)
async def admin_record_work(
    data: RecordWorkIn,
    user: CurrentUser,
    request: Request = None,
) -> ActionOut:
    require_father(user)
    entry = json.dumps({"worker": data.worker, "product_code": data.product_code, "quantity": data.quantity})
    result = log_production_json(f"[{entry}]")
    return ActionOut(message=result)


@admin_router.post("/rejection", response_model=ActionOut)
async def admin_add_rejection(data: RejectionIn, user: CurrentUser) -> ActionOut:
    require_father(user)
    from tools.rejection_tools import log_rejection as rej_log
    excluded = json.loads(data.excluded_workers)
    result = rej_log(data.year, data.month, data.product_code, data.total_qty, excluded)
    return ActionOut(message=result)


@admin_router.post("/advance", response_model=ActionOut)
async def admin_add_advance(data: AdvanceIn, user: CurrentUser) -> ActionOut:
    require_father(user)
    from tools.advance_tools import record_advance as adv_rec
    result = adv_rec(data.worker, data.amount, data.year, data.month, data.description)
    return ActionOut(message=result)


@admin_router.post("/payslip", response_model=ActionOut)
async def admin_generate_payslip(data: PayslipIn, user: CurrentUser) -> ActionOut:
    require_father(user)
    from agent_system.orchestrator import generate_payslip_tool
    result = generate_payslip_tool(data.year, data.month, data.worker or None)
    return ActionOut(message=result)


@admin_router.get("/payslips")
async def admin_list_payslips(user: CurrentUser, year: int = 0, month: int = 0) -> dict:
    require_auth(user)
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
    require_auth(user)
    from config import PDF_DIR
    filepath = PDF_DIR / f"{worker}_{year}_{month:02d}.pdf"
    if not filepath.exists():
        raise HTTPException(404, "Payslip not found")
    return FileResponse(
        str(filepath),
        filename=f"{worker}_{year}_{month:02d}.pdf",
        media_type="application/pdf",
    )



@admin_router.post("/email", response_model=ActionOut)
async def admin_send_email_report(data: EmailReportIn, user: CurrentUser) -> ActionOut:
    require_father(user)
    from tools.email_tools import send_report
    today = date.today()
    result = send_report(data.period, data.year or today.year, data.month or today.month, data.day or today.day)
    return ActionOut(message=result)


@admin_router.post("/chat", response_model=ChatOut)
async def admin_agent_chat(data: ChatIn, user: CurrentUser) -> ChatOut:
    require_father(user)
    from agent_system.orchestrator import chat
    result = await chat(data.text)
    return ChatOut(response=result)


@admin_router.post("/chat/stream")
async def admin_agent_chat_stream(data: ChatIn, user: CurrentUser) -> StreamingResponse:
    require_father(user)
    from agent_system.orchestrator import stream_chat
    return StreamingResponse(
        stream_chat(data.text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@admin_router.post("/backfill")
async def admin_backfill(user: CurrentUser) -> dict:
    require_father(user)
    from tools.database import backfill_history
    return backfill_history()
