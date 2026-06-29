import os
from config import FRONTEND_URL
if "localhost" in FRONTEND_URL or "dev" in FRONTEND_URL:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

import json
import hashlib
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from cryptography.fernet import Fernet
import base64

from config import (
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_SCOPES,
    TOKEN_DIR,
)

_fernet_key: Optional[bytes] = None


def _get_fernet() -> Fernet:
    global _fernet_key
    if _fernet_key is None:
        from config import FERNET_SECRET
        secret = FERNET_SECRET or GMAIL_CLIENT_SECRET
        raw = hashlib.sha256(secret.encode()).digest()
        _fernet_key = base64.urlsafe_b64encode(raw)
    return Fernet(_fernet_key)


def _token_path(email: str) -> Path:
    safe = email.replace("@", "_at_").replace(".", "_dot_")
    return TOKEN_DIR / f"{safe}.token"


def get_authorization_url(redirect_uri: str) -> tuple[str, str, str]:
    client_config = {
        "web": {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES.split())
    flow.redirect_uri = redirect_uri
    flow.pkce = True
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state, flow.code_verifier


def exchange_code(state: str, redirect_uri: str, callback_url: str, code_verifier: str) -> tuple[Credentials, str]:
    client_config = {
        "web": {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES.split(), state=state)
    flow.redirect_uri = redirect_uri
    flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=callback_url)
    creds = flow.credentials

    email = "unknown@email.com"
    try:
        from googleapiclient.discovery import build
        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        fetched = user_info.get("email", "")
        if fetched:
            email = fetched
        else:
            raise ValueError("Google returned empty email")
    except Exception as e:
        print(f"[OAuth] Failed to fetch user email: {e}")

    return creds, email


def save_token(email: str, creds: Credentials):
    token_data = {
        "email": email,
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    raw = json.dumps(token_data).encode()
    encrypted = _get_fernet().encrypt(raw)
    _token_path(email).write_bytes(encrypted)


def load_token(email: str) -> Optional[Credentials]:
    path = _token_path(email)
    if not path.exists():
        return None
    try:
        encrypted = path.read_bytes()
        raw = _get_fernet().decrypt(encrypted)
        token_data = json.loads(raw.decode())
        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data.get("scopes"),
        )
        return creds
    except Exception:
        return None


def get_valid_credentials(email: str) -> Optional[Credentials]:
    creds = load_token(email)
    if not creds:
        return None
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_token(email, creds)
    return creds


def list_authorized_users() -> list[str]:
    users = []
    for f in TOKEN_DIR.glob("*.token"):
        try:
            encrypted = f.read_bytes()
            raw = _get_fernet().decrypt(encrypted)
            data = json.loads(raw.decode())
            if "email" in data:
                users.append(data["email"])
        except Exception:
            continue
    return users


def delete_token(email: str):
    path = _token_path(email)
    if path.exists():
        path.unlink()


def has_token(email: str) -> bool:
    return load_token(email) is not None


def is_admin_email(email: str) -> bool:
    from config import FATHER_EMAIL
    return email == FATHER_EMAIL


def create_auth_token(email: str, is_admin: bool, session_id: str) -> str:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    token_data = {
        "email": email,
        "is_admin": is_admin,
        "session_id": session_id,
        "iat": now.isoformat(),
        "exp": (now + timedelta(hours=1)).isoformat(),
    }
    raw = json.dumps(token_data)
    return _get_fernet().encrypt(raw.encode()).decode()


def verify_auth_token(token: str) -> dict | None:
    from datetime import datetime, timezone
    try:
        raw = _get_fernet().decrypt(token.encode())
        data = json.loads(raw.decode())
        exp = datetime.fromisoformat(data.get("exp", ""))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            return None
        return data
    except Exception:
        return None
