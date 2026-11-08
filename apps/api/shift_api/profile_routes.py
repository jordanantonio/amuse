"""Shift V1 profiles, credential wallet (CRED-1/2), work history and notifications."""

import base64
import binascii
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_hex
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from .auth import Database
from .catalog import coordinates
from .config import settings
from .market_common import audit, require_org, require_worker, user_org
from .market_models import (
    Credential,
    CredentialType,
    Notification,
    OrgMember,
    User,
    WorkHistory,
)
from .market_schemas import (
    CredentialInput,
    CredentialTypeView,
    CredentialView,
    DocumentUpload,
    NotificationsView,
    OrgInput,
    OrgProfileView,
    OrgView,
    ProfileInput,
    ProfileView,
    UserView,
    WorkerProfileView,
    WorkHistoryInput,
    WorkHistoryView,
)
from .session import CurrentUser, sign, verify
from .wallet import (
    completeness,
    credential_name,
    days_to_expiry,
    effective_status,
    expiring_soon,
    type_map,
    user_credentials,
)

router = APIRouter(prefix="/api/v1/market", tags=["market"])
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
# Magic numbers: the declared type must match the file's first bytes.
SIGNATURES = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG"],
    "image/webp": [b"RIFF"],
}


def credential_view(c: Credential, types) -> CredentialView:
    t = types.get(c.credential_type_id) if c.credential_type_id else None
    return CredentialView(
        id=c.id,
        credential_type_id=c.credential_type_id,
        name=credential_name(c, types),
        category=t.category if t else "Other",
        issuer=c.issuer,
        number=c.number,
        issued_on=c.issued_on,
        expires_on=c.expires_on,
        status=effective_status(c),
        expiring_soon=expiring_soon(c),
        days_to_expiry=days_to_expiry(c),
        has_document=bool(c.document_path),
        document_name=c.document_name,
        rejection_reason=c.rejection_reason,
    )


def profile_view(db, user: User) -> ProfileView:
    profile = require_worker(db, user)
    types = type_map(db)
    history = db.scalars(
        select(WorkHistory)
        .where(WorkHistory.user_id == user.id)
        .order_by(WorkHistory.start_date.desc())
    )
    return ProfileView(
        user=UserView.model_validate(user),
        profile=WorkerProfileView.model_validate(profile),
        credentials=[credential_view(c, types) for c in user_credentials(db, user.id)],
        history=[WorkHistoryView.model_validate(h) for h in history],
        completeness=completeness(db, user, profile),
    )


@router.get("/credential-types", response_model=list[CredentialTypeView])
def credential_types(db: Database):
    return list(db.scalars(select(CredentialType).order_by(CredentialType.category, CredentialType.name)))


@router.get("/me/profile", response_model=ProfileView)
def my_profile(db: Database, user: CurrentUser):
    return profile_view(db, user)


@router.put("/me/profile", response_model=ProfileView)
def update_profile(payload: ProfileInput, db: Database, user: CurrentUser):
    profile = require_worker(db, user)
    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data:
        user.full_name = data.pop("full_name")
    if "city" in data:
        profile.lat, profile.lng = coordinates(data["city"])
    for key, value in data.items():
        setattr(profile, key, value)
    if (
        profile.rate_min_cents is not None
        and profile.rate_max_cents is not None
        and profile.rate_max_cents < profile.rate_min_cents
    ):
        raise HTTPException(422, "The maximum rate must be at least the minimum")
    db.commit()
    return profile_view(db, user)


def org_view(db, org) -> OrgProfileView:
    types = type_map(db)
    creds = db.scalars(
        select(Credential).where(Credential.owner_org_id == org.id).order_by(Credential.created_at)
    )
    return OrgProfileView(
        organization=OrgView.model_validate(org),
        credentials=[credential_view(c, types) for c in creds],
    )


@router.get("/org/profile", response_model=OrgProfileView)
def my_org(db: Database, user: CurrentUser):
    return org_view(db, require_org(db, user))


@router.put("/org/profile", response_model=OrgProfileView)
def update_org(payload: OrgInput, db: Database, user: CurrentUser):
    org = require_org(db, user)
    data = payload.model_dump(exclude_unset=True)
    if "city" in data:
        org.lat, org.lng = coordinates(data["city"])
    for key, value in data.items():
        setattr(org, key, value)
    db.commit()
    return org_view(db, org)


# ---------- Credentials ----------


def owned_credential(db, user: User, credential_id: str) -> Credential:
    c = db.get(Credential, credential_id)
    org = user_org(db, user)
    if not c or not (
        c.owner_user_id == user.id or (org is not None and c.owner_org_id == org.id)
    ):
        raise HTTPException(404, "Credential not found")
    return c


def apply_input(db, c: Credential, payload: CredentialInput, owner_kind: str) -> None:
    if payload.credential_type_id:
        t = db.get(CredentialType, payload.credential_type_id)
        if not t:
            raise HTTPException(422, "Unknown credential type")
        if t.applies_to != owner_kind:
            raise HTTPException(422, "That credential type isn’t for this kind of account")
    changed = (
        c.credential_type_id != payload.credential_type_id
        or (c.number or None) != (payload.number or None)
        or c.issued_on != payload.issued_on
        or c.expires_on != payload.expires_on
    )
    c.credential_type_id = payload.credential_type_id
    c.custom_name = None if payload.credential_type_id else (payload.custom_name or "").strip()
    c.issuer = payload.issuer.strip()
    c.number = (payload.number or "").strip() or None
    c.issued_on = payload.issued_on
    c.expires_on = payload.expires_on
    if changed and c.status in {"verified", "rejected"}:
        # Edited facts need a fresh review before they count as verified again.
        c.status = "pending" if c.document_path else "self_reported"
        c.reviewed_by = c.reviewed_at = c.rejection_reason = None


def wallet_owner_view(db, user: User, c: Credential):
    return credential_view(c, type_map(db))


@router.post("/credentials", response_model=CredentialView, status_code=201)
def add_credential(payload: CredentialInput, db: Database, user: CurrentUser):
    if payload.scope == "org":
        org = require_org(db, user)
        c = Credential(owner_org_id=org.id, status="self_reported")
        kind = "org"
    else:
        require_worker(db, user)
        c = Credential(owner_user_id=user.id, status="self_reported")
        kind = "worker"
    apply_input(db, c, payload, kind)
    db.add(c)
    db.flush()
    audit(db, user, "credential.added", "credentials", c.id)
    db.commit()
    return wallet_owner_view(db, user, c)


@router.put("/credentials/{credential_id}", response_model=CredentialView)
def edit_credential(credential_id: str, payload: CredentialInput, db: Database, user: CurrentUser):
    c = owned_credential(db, user, credential_id)
    apply_input(db, c, payload, "org" if c.owner_org_id else "worker")
    audit(db, user, "credential.edited", "credentials", c.id)
    db.commit()
    return wallet_owner_view(db, user, c)


def document_file(c: Credential) -> Path | None:
    return Path(settings.upload_dir) / c.document_path if c.document_path else None


@router.delete("/credentials/{credential_id}")
def delete_credential(credential_id: str, db: Database, user: CurrentUser):
    c = owned_credential(db, user, credential_id)
    path = document_file(c)
    db.delete(c)
    audit(db, user, "credential.deleted", "credentials", credential_id)
    db.commit()
    if path:
        path.unlink(missing_ok=True)
    return {"deleted": True}


@router.post("/credentials/{credential_id}/document", response_model=CredentialView)
def upload_document(credential_id: str, payload: DocumentUpload, db: Database, user: CurrentUser):
    c = owned_credential(db, user, credential_id)
    try:
        body = base64.b64decode(payload.data_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "The file could not be read. Try uploading it again.") from None
    if len(body) > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, "Files must be 5 MB or smaller")
    if not any(body.startswith(sig) for sig in SIGNATURES[payload.content_type]):
        raise HTTPException(422, "The file doesn’t match its type. Upload a PDF or a photo.")
    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    old = document_file(c)
    name = token_hex(16) + EXTENSIONS[payload.content_type]
    (folder / name).write_bytes(body)
    c.document_path = name
    c.document_name = Path(payload.filename).name[:200]
    c.document_type = payload.content_type
    if c.status in {"self_reported", "rejected", "verified"}:
        # New proof goes to the review queue (CRED-3).
        c.status = "pending"
        c.reviewed_by = c.reviewed_at = c.rejection_reason = None
    audit(db, user, "credential.document_uploaded", "credentials", c.id)
    db.commit()
    if old and old.name != name:
        old.unlink(missing_ok=True)
    return wallet_owner_view(db, user, c)


def can_view_document(db, viewer: User, c: Credential) -> bool:
    """Owner, Shift admins, and businesses the worker has applied to (privacy note)."""
    if viewer.is_admin or c.owner_user_id == viewer.id:
        return True
    org = user_org(db, viewer)
    if org and c.owner_org_id == org.id:
        return True
    if org and c.owner_user_id:
        try:
            from .flow import applied_to_org
        except ImportError:
            return False
        return applied_to_org(db, c.owner_user_id, org.id)
    return False


@router.get("/credentials/{credential_id}/document-link")
def document_link(credential_id: str, db: Database, user: CurrentUser):
    c = db.get(Credential, credential_id)
    if not c or not c.document_path or not can_view_document(db, user, c):
        raise HTTPException(404, "Document not found")
    token = sign({"typ": "file", "cid": c.id, "path": c.document_path}, 5)
    return {"url": f"/api/v1/market/files/{token}", "expires_in_seconds": 300}


@router.get("/files/{token}")
def serve_file(token: str, db: Database):
    claims = verify(token, "file")
    c = db.get(Credential, claims["cid"])
    if not c or c.document_path != claims["path"]:
        raise HTTPException(404, "Document not found")
    path = document_file(c)
    if not path or not path.exists():
        raise HTTPException(404, "Document not found")
    return FileResponse(
        path,
        media_type=c.document_type or "application/octet-stream",
        filename=c.document_name or path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


# ---------- Work history ----------


def owned_history(db, user: User, entry_id: str) -> WorkHistory:
    h = db.get(WorkHistory, entry_id)
    if not h or h.user_id != user.id:
        raise HTTPException(404, "Work history entry not found")
    return h


@router.post("/work-history", response_model=WorkHistoryView, status_code=201)
def add_history(payload: WorkHistoryInput, db: Database, user: CurrentUser):
    require_worker(db, user)
    h = WorkHistory(user_id=user.id, **payload.model_dump())
    db.add(h)
    db.commit()
    return h


@router.put("/work-history/{entry_id}", response_model=WorkHistoryView)
def edit_history(entry_id: str, payload: WorkHistoryInput, db: Database, user: CurrentUser):
    h = owned_history(db, user, entry_id)
    if h.engagement_id:
        raise HTTPException(409, "Completed Shift contracts can’t be edited")
    for key, value in payload.model_dump().items():
        setattr(h, key, value)
    db.commit()
    return h


@router.delete("/work-history/{entry_id}")
def delete_history(entry_id: str, db: Database, user: CurrentUser):
    h = owned_history(db, user, entry_id)
    if h.engagement_id:
        raise HTTPException(409, "Completed Shift contracts stay on your record")
    db.delete(h)
    db.commit()
    return {"deleted": True}


# ---------- Notifications (NAV-2) ----------


def work_badge(db, user: User) -> int:
    try:
        from .flow import badge_count
    except ImportError:
        return 0
    return badge_count(db, user)


@router.get("/notifications", response_model=NotificationsView)
def notifications(db: Database, user: CurrentUser):
    items = list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(30)
        )
    )
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return NotificationsView(unread=unread or 0, work_badge=work_badge(db, user), items=items)


@router.post("/notifications/read")
def mark_read(db: Database, user: CurrentUser):
    now = datetime.now(timezone.utc)
    for n in db.scalars(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ):
        n.read_at = now
    db.commit()
    return {"ok": True}


def notify(db, user_ids, type_: str, **payload) -> None:
    for uid in set(user_ids):
        db.add(Notification(user_id=uid, type=type_, payload=payload))


def org_user_ids(db, org_id: str) -> list[str]:
    return list(db.scalars(select(OrgMember.user_id).where(OrgMember.org_id == org_id)))
