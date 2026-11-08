from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Membership, Project

Database = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=4)
def jwks_client(issuer: str):
    return jwt.PyJWKClient(issuer + "/.well-known/jwks.json", lifespan=300, timeout=5)


def verify_token(token: str) -> str:
    try:
        key = jwks_client(settings.issuer).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["ES256", "RS256"],
            issuer=settings.issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject or len(subject) > 100:
            raise jwt.InvalidTokenError("Invalid subject")
        return subject
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Identity verification temporarily unavailable") from None
    except jwt.PyJWTError:
        raise HTTPException(
            401, "Invalid or expired session", headers={"WWW-Authenticate": "Bearer"}
        ) from None


def current_persona(
    db: Database,
    x_demo_persona: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> Membership:
    if settings.demo_mode:
        persona = db.get(Membership, x_demo_persona or "demo-manager")
        if not persona:
            raise HTTPException(401, "Unknown demo persona")
        return persona
    if x_demo_persona is not None:
        raise HTTPException(400, "Demo identity is disabled")
    # Fail closed even when called outside application startup (e.g. dependency tests).
    try:
        settings.validate_hosted()
    except ValueError:
        raise HTTPException(503, "Hosted identity is not configured") from None
    if not credentials:
        raise HTTPException(401, "Sign in required", headers={"WWW-Authenticate": "Bearer"})
    subject = verify_token(credentials.credentials)
    db.info["auth_subject"] = subject
    # The first query starts a transaction; database.after_begin installs LOCAL context.
    actor = db.scalar(select(Membership).where(Membership.auth_subject == subject))
    if not actor:
        raise HTTPException(403, "No organization membership. Contact your administrator.")
    return actor


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
