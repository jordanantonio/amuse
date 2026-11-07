from typing import Annotated
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Membership, Project

Database = Annotated[Session, Depends(get_db)]


def current_persona(
    db: Database, x_demo_persona: Annotated[str | None, Header()] = None
) -> Membership:
    if not settings.demo_mode:
        raise HTTPException(503, "Production auth is not configured; local demo access is disabled")
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
