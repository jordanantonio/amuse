"""Operator-only membership provisioning for an existing Supabase Auth user.
No role is inferred from client-editable JWT user metadata. Requires DB credentials.
"""

import sys, argparse
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from sqlalchemy import select
from shift_api.database import SessionLocal
from shift_api.models import Membership, Organization, Worker

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subject", required=True, type=UUID)
    p.add_argument("--organization", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", choices=["worker", "manager", "admin"], required=True)
    args = p.parse_args()
    with SessionLocal() as db:
        if not db.get(Organization, args.organization):
            raise SystemExit("Organization does not exist")
        if db.scalar(select(Membership).where(Membership.auth_subject == str(args.subject))):
            raise SystemExit("This auth subject already has a membership")
        m = Membership(
            organization_id=args.organization,
            auth_subject=str(args.subject),
            name=args.name,
            role=args.role,
        )
        db.add(m)
        db.flush()
        if args.role == "worker":
            db.add(
                Worker(
                    membership_id=m.id,
                    organization_id=args.organization,
                    name=args.name,
                    title="Professional",
                    location="Edmonton, AB",
                    hourly_rate_cents=0,
                    employment_type="contractor",
                    work_modes=["on_site"],
                    color="#8e7bc2",
                )
            )
        db.commit()
        print("Membership provisioned:", m.id)
