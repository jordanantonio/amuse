from typing import Annotated
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from functools import lru_cache
import jwt
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Membership, Project

Database = Annotated[Session, Depends(get_db)]


def current_persona(
    db: Database,
    x_demo_persona: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Membership:
    if not settings.demo_mode:
        if not settings.supabase_url:
            raise HTTPException(503, "Supabase identity is not configured")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Sign in required")
        try:
            token = authorization.removeprefix("Bearer ")
            issuer = settings.supabase_url.rstrip("/") + "/auth/v1"
            key = jwks_client(issuer).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["ES256", "RS256"],
                audience=settings.jwt_audience,
                issuer=issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except Exception:
            raise HTTPException(401, "Invalid or expired Supabase session")
        persona = db.scalar(select(Membership).where(Membership.auth_subject == claims["sub"]))
        if not persona:
            raise HTTPException(
                403, "Your account has no organization membership. Ask your administrator."
            )
        return persona
    persona = db.get(Membership, x_demo_persona or "demo-manager")
    if not persona:
        raise HTTPException(401, "Unknown demo persona")
    return persona


Actor = Annotated[Membership, Depends(current_persona)]


def managed_project(db: Session, actor: Membership, project_id: str) -> Project:
    p = db.get(Project, project_id)
    if not p or p.organization_id != actor.organization_id:
        raise HTTPException(404, "Project not found")
    if actor.role not in {"manager", "admin"}:
        raise HTTPException(403, "A manager or administrator is required")
    if actor.role == "manager" and p.manager_id != actor.id:
        raise HTTPException(403, "Project is outside your managed scope")
    return p


@lru_cache(maxsize=4)
def jwks_client(issuer):
    return jwt.PyJWKClient(issuer + "/.well-known/jwks.json", cache_keys=True, lifespan=300)
