"""Bind an administrator-created Supabase account to one SHIFT organization.

Run with privileged migration credentials, never from an HTTP endpoint.
No Supabase secret or password is accepted as a command-line argument.
"""

import argparse
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from shift_api.config import settings
from shift_api.database import SessionLocal
from shift_api.models import Membership, Organization, Worker
from sqlalchemy import select


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True, type=UUID, help="Supabase Auth user UUID")
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--organization-name", help="Required when creating an organization")
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=["worker", "manager", "admin"], required=True)
    parser.add_argument(
        "--worker-id", help="Explicitly bind an existing worker profile in this organization"
    )
    args = parser.parse_args()
    settings.validate_hosted()
    if settings.demo_mode:
        parser.error("Provisioning is hosted-only; use migration credentials")
    with SessionLocal.begin() as db:
        subject = str(args.subject)
        membership = db.scalar(select(Membership).where(Membership.auth_subject == subject))
        if membership:
            parser.error("User already has a membership; no existing access was changed")
        org = db.get(Organization, args.organization_id)
        if not org:
            if not args.organization_name:
                parser.error("New organizations require --organization-name")
            org = Organization(id=args.organization_id, name=args.organization_name)
            db.add(org)
            db.flush()
        membership = Membership(
            organization_id=org.id, auth_subject=subject, name=args.name, role=args.role
        )
        db.add(membership)
        db.flush()
        if args.worker_id:
            worker = db.get(Worker, args.worker_id)
            if args.role != "worker" or not worker or worker.organization_id != org.id:
                parser.error(
                    "Worker binding requires a worker role and profile in the same organization"
                )
            worker.membership_id = membership.id
    print("Membership provisioned. Organization access is ready.")


if __name__ == "__main__":
    main()
