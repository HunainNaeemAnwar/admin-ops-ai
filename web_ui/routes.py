from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from config import BASE_DIR, FATHER_EMAIL
from tools.database import (
    get_db, get_all_workers, get_all_products, get_logs_for_date,
    get_worker_id, get_worker_month_production, get_daily_totals,
)
from tools.oauth_tools import (
    get_authorization_url, exchange_code, save_token,
    list_authorized_users, delete_token, get_valid_credentials,
    is_father_email,
)
from tools.production_tools import log_production_json, calc_piece_rate, get_product_info

router = APIRouter()

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
                f'<a href="/logout?email={email}" style="color:#ffd700;">Logout</a>'
            )
        else:
            html = html.replace(
                "<!--USERS-->",
                '<a href="/login" class="login-btn">Sign in with Google</a>'
            )
    return html


def get_current_user(request: Request) -> str | None:
    users = list_authorized_users()
    return users[0] if users else None


def require_father(user: str | None):
    if not user or not is_father_email(user):
        raise HTTPException(403, "Only father can perform this action")


# ── Public Routes ───────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    users = list_authorized_users()
    today = date.today()

    logs = get_logs_for_date(today.isoformat())
    present = set(l["worker_name"] for l in logs if l["status"] == "present")
    totals = get_daily_totals(today.isoformat())
    total_pieces = sum(totals.values())

    return _render(
        "index.html",
        today=today.isoformat(),
        users=users,
        daily_total=f"Rs {total_pieces * 0:,.2f}",
        daily_workers=str(len(present)),
        daily_pieces=str(total_pieces),
        daily_entries=str(len(logs)),
        daily_workers_list=", ".join(sorted(present)) or "None",
    )


@router.get("/login")
async def login(request: Request):
    base = _base_url(request)
    redirect_uri = f"{base}/oauth/callback"
    auth_url, state, code_verifier = get_authorization_url(redirect_uri)
    _oauth_states[state] = {"created": datetime.now().isoformat(), "redirect_uri": redirect_uri, "code_verifier": code_verifier}
    return RedirectResponse(auth_url)


@router.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        return HTMLResponse(f"<h2>Error: {error}</h2><a href='/'>Go back</a>", status_code=400)
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
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(email: str = None):
    if email:
        delete_token(email)
    return RedirectResponse(url="/")


@router.get("/daily")
async def daily_report(year: int = None, month: int = None, day: int = None):
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    date_str = f"{y}-{m:02d}-{d:02d}"
    logs = get_logs_for_date(date_str)
    totals = get_daily_totals(date_str)
    return {
        "date": date_str,
        "entries": [dict(l) for l in logs],
        "totals": totals,
        "total_pieces": sum(totals.values()),
    }


@router.get("/monthly")
async def monthly_report(year: int = None, month: int = None):
    today = date.today()
    y = year or today.year
    m = month or today.month
    workers = get_all_workers()
    products = get_all_products()
    product_codes = [p["code"] for p in products]
    worker_data = []
    grand_totals = {code: 0 for code in product_codes}
    for w in workers:
        entries = get_worker_month_production(w["id"], y, m)
        worker_totals = {}
        for e in entries:
            code = e["product_code"]
            worker_totals[code] = worker_totals.get(code, 0) + e["quantity"]
            grand_totals[code] = grand_totals.get(code, 0) + e["quantity"]
        if worker_totals:
            worker_data.append({"worker": w["name"], "totals": worker_totals})
    return {"year": y, "month": m, "workers": worker_data, "grand_totals": grand_totals}


@router.get("/workers")
async def workers_list():
    workers = get_all_workers()
    return {"workers": [w["name"] for w in workers]}


@router.get("/worker/{worker}")
async def worker_detail(worker: str, year: int = None, month: int = None):
    today = date.today()
    y = year or today.year
    m = month or today.month
    wid = get_worker_id(worker)
    if not wid:
        raise HTTPException(404, f"Worker '{worker}' not found")
    entries = get_worker_month_production(wid, y, m)
    return {"worker": worker, "year": y, "month": m, "entries": entries}


@router.get("/products")
async def products():
    return {"products": get_all_products()}


# ── Father-Only Routes ──────────────────────────────

@router.post("/record")
async def record_work(worker: str, product_code: str, quantity: int, request: Request):
    user = get_current_user(request)
    require_father(user)
    result = log_production_json(
        f'[{{"worker":"{worker}","product_code":"{product_code}","quantity":{quantity}}}]'
    )
    return {"status": "ok", "message": result}


@router.post("/record-text")
async def record_work_text(text: str, request: Request):
    user = get_current_user(request)
    require_father(user)
    return {"status": "error", "message": "Text input removed. Use /record with JSON or chat with the agent."}


@router.post("/rejection")
async def add_rejection(year: int, month: int, product_code: str, total_qty: int, excluded_workers: str = "[]", request: Request = None):
    user = get_current_user(request)
    require_father(user)
    import json
    from tools.rejection_tools import log_rejection as rej_log
    excluded = json.loads(excluded_workers)
    result = rej_log(year, month, product_code, total_qty, excluded)
    return {"status": "ok", "message": result}


@router.post("/advance")
async def add_advance(worker: str, amount: float, year: int, month: int, description: str = "", request: Request = None):
    user = get_current_user(request)
    require_father(user)
    from tools.advance_tools import record_advance as adv_rec
    result = adv_rec(worker, amount, year, month, description)
    return {"status": "ok", "message": result}


@router.post("/payslip")
async def generate_payslip(year: int, month: int, worker: str = "", request: Request = None):
    user = get_current_user(request)
    require_father(user)
    from agent_system.orchestrator import generate_payslip_tool
    result = generate_payslip_tool(year, month, worker or None)
    return {"status": "ok", "message": result}


@router.post("/email")
async def send_email_report(period: str = "daily", year: int = None, month: int = None, day: int = None, request: Request = None):
    user = get_current_user(request)
    require_father(user)
    from tools.email_tools import send_report
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    result = send_report(period, y, m, d)
    return {"status": "ok", "message": result}


@router.post("/chat")
async def agent_chat(text: str, request: Request = None):
    user = get_current_user(request)
    require_father(user)
    import asyncio
    from agent_system.orchestrator import chat
    result = await asyncio.to_thread(asyncio.run, chat(text))
    return {"status": "ok", "response": result}
