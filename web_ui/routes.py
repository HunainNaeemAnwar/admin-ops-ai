from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from config import BASE_DIR
from tools.excel_tools import load_product_catalog, get_all_workers, get_worker_entries
from tools.calc_tools import calc_daily_summary, calc_monthly_summary
from tools.oauth_tools import (
    get_authorization_url, exchange_code, save_token,
    list_authorized_users, delete_token,
)

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

    if "users" in kwargs:
        users = kwargs["users"]
        if users:
            html = html.replace("<!--USERS-->", f'<a href="#" style="opacity:0.9;">{users[0]}</a><a href="/logout?email={users[0]}" style="color:#ffd700;">Logout</a>')
        else:
            html = html.replace("<!--USERS-->", '<a href="/login" class="login-btn">Sign in with Google</a>')

    return html


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    users = list_authorized_users()
    today = date.today()
    try:
        daily = calc_daily_summary(today.year, today.month, today.day)
    except Exception:
        daily = None

    return _render(
        "index.html",
        today=today.isoformat(),
        users=users,
        daily_total=f'Rs {daily["total_net"]:,.2f}' if daily else "0",
        daily_workers=str(daily["workers_count"]) if daily else "0",
        daily_pieces=str(daily["total_pieces"]) if daily else "0",
        daily_entries=str(daily["entries_count"]) if daily else "0",
        daily_workers_list=", ".join(daily["workers"]) if daily and daily.get("workers") else "None",
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
    try:
        return calc_daily_summary(y, m, d)
    except Exception as e:
        return {"error": str(e)}


@router.get("/monthly")
async def monthly_report(year: int = None, month: int = None):
    today = date.today()
    y = year or today.month
    m = month or today.month
    return calc_monthly_summary(y, m)


@router.get("/workers")
async def workers_list(year: int = None, month: int = None):
    today = date.today()
    y = year or today.month
    m = month or today.month
    workers = get_all_workers(y, m)
    return {"workers": workers, "year": y, "month": m}


@router.get("/worker/{worker}")
async def worker_detail(worker: str, year: int = None, month: int = None):
    today = date.today()
    y = year or today.year
    m = month or today.month
    entries = get_worker_entries(worker, y, m)
    from tools.calc_tools import calc_worker_payslip
    payslip = calc_worker_payslip(worker, y, m)
    return {"worker": worker, "entries": entries, "payslip": payslip}


@router.post("/record")
async def record_work(worker: str, product_code: str, quantity: int):
    from tools.calc_tools import calc_piece_rate
    from tools.excel_tools import append_work_entry
    result = calc_piece_rate(product_code, quantity)
    if "error" in result:
        return {"error": result["error"]}
    append_work_entry(
        worker=worker, product_code=result["product_code"],
        description=result["description"], quantity=result["quantity"],
        rate=result["rate"], gross=result["gross"],
        tax_pct=result["tax_pct"], tax_amt=result["tax_amt"], net=result["net"],
    )
    return {"status": "ok", "net": result["net"], "gross": result["gross"]}


@router.post("/record-text")
async def record_work_text(text: str):
    import asyncio
    from agent_system.data_extractor import extract_from_text
    from tools.calc_tools import calc_piece_rate
    from tools.excel_tools import append_work_entry

    parsed = await extract_from_text(text)
    results = []
    for prod in parsed.products:
        result = calc_piece_rate(prod.product_code, prod.quantity)
        if "error" not in result:
            append_work_entry(
                worker=parsed.worker, product_code=result["product_code"],
                description=result["description"], quantity=result["quantity"],
                rate=result["rate"], gross=result["gross"],
                tax_pct=result["tax_pct"], tax_amt=result["tax_amt"], net=result["net"],
            )
            results.append(result)
    total_net = sum(r["net"] for r in results)
    return {"worker": parsed.worker, "entries": len(results), "total_net": total_net, "details": results}


@router.get("/products")
async def products():
    return {"products": load_product_catalog()}
