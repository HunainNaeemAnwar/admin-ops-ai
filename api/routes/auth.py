import json
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
import uuid

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from config import FRONTEND_URL, GMAIL_REDIRECT_URI
from api.schemas import AuthUserOut
from api.routes.common import (
    get_current_user, rate_limit_auth,
)
from services.oauth_tools import (
    _get_fernet, get_authorization_url, exchange_code, save_token,
    delete_token, is_admin_email, create_auth_token, verify_auth_token,
)
from services.database import (
    save_oauth_state, pop_oauth_state, cleanup_expired_oauth_states,
    create_session, revoke_session, log_auth_event,
)

auth_router = APIRouter()
admin_auth_router = APIRouter()


@auth_router.get("/api/auth/me", response_model=AuthUserOut)
async def api_auth_me(request: Request) -> AuthUserOut:
    raw_token = request.cookies.get("auth") or request.headers.get("x-auth-token", "")
    if not raw_token:
        return AuthUserOut()
    data = verify_auth_token(raw_token)
    if not data:
        return AuthUserOut()
    from services.database import get_session
    session = get_session(data.get("session_id", ""))
    if not session:
        return AuthUserOut()
    return AuthUserOut(
        email=data.get("email", ""),
        is_admin=data.get("is_admin", False),
        authenticated=True,
    )


@auth_router.post("/api/auth/logout")
async def api_auth_logout(request: Request) -> JSONResponse:
    raw_token = request.cookies.get("auth") or request.headers.get("x-auth-token", "")
    email = ""
    if raw_token:
        data = verify_auth_token(raw_token)
        if data:
            email = data.get("email", "")
            sid = data.get("session_id", "")
            if sid:
                revoke_session(sid)
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie("auth", path="/")
    if email:
        log_auth_event(email, "logout", request.client.host if request.client else "")
    return resp


@auth_router.post("/api/auth/refresh", response_model=AuthUserOut)
async def api_auth_refresh(request: Request) -> AuthUserOut:
    raw_token = request.cookies.get("auth") or request.headers.get("x-auth-token", "")
    if not raw_token:
        return AuthUserOut()
    data = verify_auth_token(raw_token)
    if not data:
        return AuthUserOut()
    from services.database import get_session
    session = get_session(data.get("session_id", ""))
    if not session:
        return AuthUserOut()
    sid = data["session_id"]
    revoke_session(sid)
    new_sid = str(uuid.uuid4())
    ip = request.client.host if request.client else ""
    create_session(new_sid, data["email"], data["is_admin"], ip, ttl_hours=24)
    new_token = create_auth_token(data["email"], data["is_admin"], new_sid)
    log_auth_event(data["email"], "token_refresh", ip)
    return AuthUserOut(
        email=data["email"],
        is_admin=data["is_admin"],
        authenticated=True,
        token=new_token,
    )


@admin_auth_router.get("/login")
async def admin_login(request: Request) -> RedirectResponse:
    rate_limit_auth(request)
    cleanup_expired_oauth_states()
    redirect_uri = GMAIL_REDIRECT_URI
    auth_url, state, code_verifier = get_authorization_url(redirect_uri)
    save_oauth_state(state, code_verifier, redirect_uri)
    return RedirectResponse(auth_url)


@auth_router.get("/oauth/callback", response_model=None)
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

    state_data = pop_oauth_state(state)
    if not state_data:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=expired", status_code=303)

    redirect_uri = state_data["redirect_uri"]
    code_verifier = state_data["code_verifier"]
    full_url = str(request.url)
    creds, email = exchange_code(state, redirect_uri, full_url, code_verifier)
    save_token(email, creds)

    is_admin = is_admin_email(email)
    ip = request.client.host if request.client else ""

    session_id = str(uuid.uuid4())
    create_session(session_id, email, is_admin, ip, ttl_hours=24)
    encrypted = create_auth_token(email, is_admin, session_id)
    log_auth_event(email, "login", ip)

    redirect_params = urlencode({"token": encrypted, "is_admin": str(is_admin).lower()})
    redirect_path = f"{FRONTEND_URL}/auth/callback?{redirect_params}"
    return RedirectResponse(url=redirect_path, status_code=303)


@admin_auth_router.get("/logout")
async def admin_logout(request: Request, email: str = None) -> RedirectResponse:
    raw_token = request.cookies.get("auth") or request.headers.get("x-auth-token", "")
    if raw_token:
        data = verify_auth_token(raw_token)
        if data:
            sid = data.get("session_id", "")
            if sid:
                revoke_session(sid)
            email = data.get("email", email or "")
    if email:
        delete_token(email)
        log_auth_event(email, "logout", request.client.host if request.client else "")
    resp = RedirectResponse(url="/admin")
    resp.set_cookie("auth", "", max_age=0, path="/")
    return resp
