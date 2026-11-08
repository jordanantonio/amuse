"""Google OAuth (sign-in and incremental Calendar consent).

Dormant until SHIFT_GOOGLE_CLIENT_ID and SHIFT_GOOGLE_CLIENT_SECRET are set. Uses only
the standard library for HTTP so no extra dependency is needed.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
import jwt
from fastapi import HTTPException
from .config import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
SIGN_IN_SCOPES = "openid email profile"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def enabled() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def redirect_uri() -> str:
    return settings.public_base_url.rstrip("/") + "/api/v1/auth/google/callback"


def authorize_url(state: str, scope: str, *, login_hint: str | None = None, offline=False) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": scope,
        "state": state,
        "include_granted_scopes": "true",
    }
    if offline:
        # A refresh token is needed to write Calendar events after this request.
        params |= {"access_type": "offline", "prompt": "consent"}
    if login_hint:
        params["login_hint"] = login_hint
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def _post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as error:
        raise HTTPException(502, f"Google rejected the request ({error.code}). Try again.") from None
    except urllib.error.URLError:
        raise HTTPException(502, "Could not reach Google. Check the connection and try again.") from None


def exchange_code(code: str) -> dict:
    return _post_form(
        TOKEN_URL,
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
    )


def refresh_access_token(refresh_token: str) -> str:
    tokens = _post_form(
        TOKEN_URL,
        {
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
    )
    return tokens["access_token"]


@lru_cache(maxsize=1)
def _jwks():
    return jwt.PyJWKClient(CERTS_URL, cache_keys=True, lifespan=3600)


def verify_id_token(id_token: str) -> dict:
    try:
        key = _jwks().get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            key.key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except Exception:
        raise HTTPException(401, "Google sign-in could not be verified. Try again.") from None
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(401, "Google sign-in could not be verified. Try again.")
    if not claims.get("email_verified"):
        raise HTTPException(403, "Your Google email address is not verified.")
    return claims


def encrypt(value: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(settings.token_encryption_key.encode()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(settings.token_encryption_key.encode()).decrypt(value.encode()).decode()


def calendar_enabled() -> bool:
    return enabled() and bool(settings.token_encryption_key)


def calendar_request(method: str, path: str, access_token: str, body: dict | None = None):
    url = "https://www.googleapis.com/calendar/v3" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {access_token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        if error.code in (404, 410) and method == "DELETE":
            return {}
        raise HTTPException(502, f"Google Calendar rejected the request ({error.code}).") from None
    except urllib.error.URLError:
        raise HTTPException(502, "Could not reach Google Calendar. Try again.") from None
