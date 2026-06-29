import json
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import Request, HTTPException, Depends

import time
from collections import defaultdict

from config import FRONTEND_URL
from services.oauth_tools import _get_fernet, is_admin_email, verify_auth_token
from services.database import get_session

_auth_rate_limit: dict[str, list[float]] = defaultdict(list)


def rate_limit_auth(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - 60
    timestamps = _auth_rate_limit[ip]
    timestamps[:] = [t for t in timestamps if t > cutoff]
    timestamps.append(now)
    if len(timestamps) > 10:
        raise HTTPException(429, "Too many auth requests. Try again later.")


def _cleanup_expired_states(state_dict: dict[str, dict]):
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    expired = [s for s, d in state_dict.items() if datetime.fromisoformat(d["created"]) < cutoff]
    for s in expired:
        state_dict.pop(s, None)


def require_csrf(request: Request):
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    if not origin and not referer:
        raise HTTPException(403, "CSRF: origin or referer header required")
    allowed = FRONTEND_URL.rstrip("/")
    if origin and not origin.rstrip("/").startswith(allowed):
        raise HTTPException(403, "CSRF: origin not allowed")
    if referer and not referer.rstrip("/").startswith(allowed):
        raise HTTPException(403, "CSRF: referer not allowed")


def _base_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host", request.url.hostname)
    port = request.url.port
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _decrypt_auth_cookie(request: Request) -> str | None:
    raw_token = request.cookies.get("auth") or request.headers.get("x-auth-token", "")
    if not raw_token:
        return None
    data = verify_auth_token(raw_token)
    if not data:
        return None
    session = get_session(data.get("session_id", ""))
    if not session:
        return None
    return data.get("email", "")


def get_current_user(request: Request) -> str | None:
    email = _decrypt_auth_cookie(request)
    if email:
        return email
    return None


CurrentUser = Annotated[str | None, Depends(get_current_user)]


def require_admin(user: str | None):
    if not user or not is_admin_email(user):
        raise HTTPException(403, "Only admin can perform this action")


def require_auth(user: str | None):
    if not user:
        raise HTTPException(401, "Authentication required")


def _check_auto_archive():
    today = date.today()
    if today.day != 1:
        return
    prev_month = today.month - 1 or 12
    prev_year = today.year if today.month > 1 else today.year - 1
    from services.database import is_month_archived
    if is_month_archived(prev_year, prev_month):
        return
    from services.database import get_active_workers, get_all_products, insert_worker_history
    from services.database import get_worker_daily_breakdown
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
