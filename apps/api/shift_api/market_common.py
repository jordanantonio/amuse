"""Shared helpers for Shift V1 routes: the acting context, handles and audit log."""

import re
from secrets import token_hex
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .market_models import AuditLog, OrgMember, User, WorkerProfile
from .models import Organization


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "member"


def unique_handle(db: Session, base: str, model, column) -> str:
    handle = slug(base)
    while db.scalar(select(column).where(column == handle)):
        handle = f"{slug(base)[:33]}-{token_hex(3)}"
    return handle


def user_org(db: Session, user: User) -> Organization | None:
    member = db.scalar(select(OrgMember).where(OrgMember.user_id == user.id).limit(1))
    return db.get(Organization, member.org_id) if member else None


def require_worker(db: Session, user: User) -> WorkerProfile:
    profile = db.get(WorkerProfile, user.id)
    if user.default_mode != "worker" or not profile:
        raise HTTPException(403, "This action is for worker accounts")
    return profile


def require_org(db: Session, user: User, kind: str | None = None) -> Organization:
    org = user_org(db, user)
    if not org or user.default_mode not in {"business", "agency"}:
        raise HTTPException(403, "This action is for business and agency accounts")
    if kind and org.kind != kind:
        raise HTTPException(403, f"This action is for {kind} accounts")
    return org


def audit(db: Session, actor: User | None, action: str, table: str, target: str, **details):
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            target_table=table,
            target_id=target,
            details=details,
        )
    )
