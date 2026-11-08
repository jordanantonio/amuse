"""Shift V1 browser sessions: a signed, httpOnly cookie holding the user id.

The cookie is issued by the API (through the Next.js same-origin proxy) after Google
sign-in, or after the local demo sign-in when SHIFT_DEMO_MODE is on.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import Cookie, Depends, HTTPException, Response
from .auth import Database
from .config import settings
from .market_models import User

COOKIE = "shift_session"
STATE_COOKIE = "shift_oauth_state"
SESSION_DAYS = 30
DEMO_SECRET = "shift-local-demo-only-session-secret-change-me"


def secret() -> str:
    if settings.session_secret:
        return settings.session_secret
    if settings.demo_mode:
        return DEMO_SECRET
    raise HTTPException(503, "Sessions are not configured: set SHIFT_SESSION_SECRET")


def sign(payload: dict, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {**payload, "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(claims, secret(), algorithm="HS256")


def verify(token: str, typ: str) -> dict:
    try:
        claims = jwt.decode(token, secret(), algorithms=["HS256"], options={"require": ["exp"]})
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session has expired. Sign in again.") from None
    if claims.get("typ") != typ:
        raise HTTPException(401, "Invalid session")
    return claims


def start_session(response: Response, user: User) -> None:
    token = sign({"typ": "session", "sub": user.id}, SESSION_DAYS * 24 * 60)
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def end_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def optional_user(
    db: Database, shift_session: Annotated[str | None, Cookie()] = None
) -> User | None:
    if not shift_session:
        return None
    try:
        claims = verify(shift_session, "session")
    except HTTPException:
        return None
    return db.get(User, claims.get("sub"))


def current_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if not user:
        raise HTTPException(401, "Sign in required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def safe_next(path: str | None, default: str = "/home") -> str:
    """Only allow same-site relative redirects (no open redirects)."""
    if path and path.startswith("/") and not path.startswith("//") and "\\" not in path:
        return path
    return default
