"""Shift V1 sign-in: Google OAuth when configured, otherwise the local demo sign-in."""

import secrets
from urllib.parse import urlencode
from typing import Annotated
from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from . import google
from .auth import Database
from .config import settings
from .market_common import user_org
from .market_models import User
from .market_schemas import DemoAccount, DemoSignIn
from .session import STATE_COOKIE, end_session, safe_next, sign, start_session, verify

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
DEMO_DOMAIN = "@demo.shift.local"


@router.get("/config")
def auth_config():
    return {
        "google": google.enabled(),
        "calendar": google.calendar_enabled(),
        "demo": settings.demo_mode,
    }


def oauth_redirect(purpose: str, scope: str, next_path: str, **extra) -> RedirectResponse:
    nonce = secrets.token_urlsafe(16)
    state = sign({"typ": "oauth", "purpose": purpose, "nonce": nonce, "next": next_path, **extra}, 10)
    response = RedirectResponse(
        google.authorize_url(
            state, scope, login_hint=extra.get("hint"), offline=purpose == "calendar"
        ),
        status_code=303,
    )
    response.set_cookie(
        STATE_COOKIE,
        nonce,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/api/v1/auth",
    )
    return response


@router.get("/google/start")
def google_start(next: str | None = None):
    if not google.enabled():
        if settings.demo_mode:
            # Honest fallback: no Google client is configured on this server.
            target = safe_next(next)
            path = "/signin/demo" if target == "/home" else "/signin/demo?" + urlencode({"next": target})
            return RedirectResponse(path, status_code=303)
        return RedirectResponse("/?error=google-not-configured", status_code=303)
    return oauth_redirect("signin", google.SIGN_IN_SCOPES, safe_next(next))


@router.get("/google/callback")
def google_callback(
    db: Database,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    shift_oauth_state: Annotated[str | None, Cookie()] = None,
    shift_session: Annotated[str | None, Cookie()] = None,
):
    if error or not code or not state:
        return RedirectResponse("/?error=google-cancelled", status_code=303)
    claims = verify(state, "oauth")
    if not shift_oauth_state or not secrets.compare_digest(claims["nonce"], shift_oauth_state):
        raise HTTPException(400, "Sign-in request expired. Start again from the sign-in page.")
    tokens = google.exchange_code(code)
    if claims["purpose"] == "calendar":
        from .calendar_routes import finish_calendar_connect

        return finish_calendar_connect(db, claims, tokens, shift_session)
    if claims["purpose"] != "signin":
        raise HTTPException(400, "Unknown sign-in request")
    identity = google.verify_id_token(tokens["id_token"])
    user = db.scalar(select(User).where(User.google_sub == identity["sub"])) or db.scalar(
        select(User).where(User.email == identity["email"].lower())
    )
    if not user:
        user = User(email=identity["email"].lower(), full_name=identity.get("name") or "")
        db.add(user)
    user.google_sub = identity["sub"]
    user.avatar_url = identity.get("picture") or user.avatar_url
    if not user.full_name:
        user.full_name = identity.get("name") or identity["email"].split("@")[0]
    db.commit()
    target = safe_next(claims.get("next")) if user.onboarded else "/onboarding"
    response = RedirectResponse(target, status_code=303)
    start_session(response, user)
    response.delete_cookie(STATE_COOKIE, path="/api/v1/auth")
    return response


def require_demo():
    if not settings.demo_mode:
        raise HTTPException(404, "Demo sign-in is disabled")


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts(db: Database):
    require_demo()
    accounts = []
    users = db.scalars(select(User).where(User.email.like("%" + DEMO_DOMAIN)).order_by(User.email))
    for user in users:
        org = user_org(db, user)
        label = (
            "Shift admin"
            if user.is_admin
            else f"{org.name} ({org.kind})"
            if org
            else "Worker"
            if user.default_mode == "worker"
            else "New account"
        )
        accounts.append(
            DemoAccount(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                mode=user.default_mode,
                label=label,
            )
        )
    return accounts


@router.post("/demo")
def demo_sign_in(payload: DemoSignIn, db: Database, response: Response, next: str | None = None):
    require_demo()
    if payload.user_id:
        user = db.get(User, payload.user_id)
        if not user or not user.email.endswith(DEMO_DOMAIN):
            raise HTTPException(404, "Demo account not found")
    else:
        if not payload.full_name:
            raise HTTPException(422, "Enter a name for the new demo account")
        email = (payload.email or f"user-{secrets.token_hex(4)}{DEMO_DOMAIN}").lower()
        if not email.endswith(DEMO_DOMAIN):
            email = email.split("@")[0] + DEMO_DOMAIN
        if db.scalar(select(User.id).where(User.email == email)):
            raise HTTPException(409, "That demo email is already used")
        user = User(email=email, full_name=payload.full_name)
        db.add(user)
        db.commit()
    start_session(response, user)
    return {"next": safe_next(next) if user.onboarded else "/onboarding"}


@router.post("/signout")
def sign_out(response: Response):
    end_session(response)
    return {"signed_out": True}
