"""Fictional Shift V1 marketplace fixture (SEED-1 to SEED-4). Never a production seed.

All demo accounts use the reserved @demo.shift.local domain so the local demo sign-in
can list them and the demo reset can recognise them.
"""

from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from .catalog import coordinates
from .market_models import OrgMember, User, WorkerProfile
from .models import Organization

D = "@demo.shift.local"

ORGS = [
    # id, name, kind, city, industry, about, verification
    (
        "northline",
        "Northline Homes",
        "business",
        "Edmonton",
        "Residential construction",
        "Edmonton homebuilder delivering 40 to 60 single-family homes a year.",
        "verified",
    ),
    (
        "prairie-harvest",
        "Prairie Harvest Foods",
        "business",
        "Leduc",
        "Food processing",
        "Food-processing plant in Leduc running two production lines year round.",
        "verified",
    ),
    (
        "nisku-fab",
        "Nisku Fabrication Works",
        "business",
        "Nisku",
        "Manufacturing",
        "Structural steel and pipe-spool fabrication shop serving energy projects.",
        "unverified",
    ),
    (
        "timberline",
        "Timberline Framing Crew",
        "agency",
        "Sherwood Park",
        "Residential construction",
        "Framing crew of 14 carpenters and labourers working the Edmonton region.",
        "verified",
    ),
    (
        "liftright",
        "LiftRight Staffing",
        "agency",
        "Edmonton",
        "Staffing",
        "Supplies certified forklift operators and warehouse crews on short notice.",
        "unverified",
    ),
]

OWNERS = [
    # user id, name, org id, link to crew-planner membership
    ("u-alex", "Alex Morgan", "northline", "demo-manager"),
    ("u-priya", "Priya Desai", "prairie-harvest", None),
    ("u-marcus", "Marcus Lee", "nisku-fab", None),
    ("u-dana", "Dana Whitford", "timberline", None),
    ("u-omar", "Omar Haddad", "liftright", None),
]

WORKERS = [
    # user id, name, headline, trades, city, radius km, rate min, rate max, bio
    (
        "u-maya",
        "Maya Brooks",
        "Journeyperson electrician, 9 yrs",
        ["Electrical", "General labour"],
        "Edmonton",
        60,
        4200,
        5200,
        "Residential and light-commercial wiring. Comfortable leading a small crew.",
    ),
    (
        "u-noah",
        "Noah Williams",
        "Structural welder, 7 yrs",
        ["Welding", "Pipefitting"],
        "Leduc",
        80,
        4000,
        5000,
        "CWB-certified on structural and pipe. Shop and field work.",
    ),
    (
        "u-ella",
        "Ella Thompson",
        "Finish carpenter, 5 yrs",
        ["Carpentry", "Framing"],
        "St. Albert",
        50,
        3400,
        4200,
        "Trim, stairs and cabinetry install. Own tools and truck.",
    ),
    (
        "u-liam",
        "Liam Patel",
        "Equipment operator, 11 yrs",
        ["Heavy equipment", "General labour"],
        "Spruce Grove",
        120,
        3800,
        4800,
        "Telehandler, loader and skid steer. Clean safety record.",
    ),
    (
        "u-sofia",
        "Sofia Rivera",
        "Apprentice electrician, level 3",
        ["Electrical"],
        "Edmonton",
        40,
        2800,
        3400,
        "Third-year apprentice looking for hours toward my ticket.",
    ),
    (
        "u-isla",
        "Isla Nguyen",
        "Concrete finisher, 6 yrs",
        ["Concrete", "General labour"],
        "Sherwood Park",
        60,
        3200,
        4000,
        "Flatwork, foundations and forming.",
    ),
    (
        "u-lucas",
        "Lucas Martin",
        "Framer, 4 yrs",
        ["Framing", "Carpentry"],
        "Edmonton",
        70,
        3000,
        3800,
        "Wall and roof framing on production homes.",
    ),
    (
        "u-amelia",
        "Amelia Singh",
        "Forklift operator, 8 yrs",
        ["Forklift & warehouse", "Food processing"],
        "Leduc",
        50,
        2600,
        3200,
        "Counterbalance and reach trucks in food and cold-storage plants.",
    ),
]


# uid -> [(credential type, stored status, issued days ago, expires in days | None, number)]
WALLETS = {
    "u-maya": [
        ("ab-journeyperson", "verified", 2900, None, "AB-JP-448120"),
        ("red-seal", "verified", 2900, None, "RS-309-ELEC"),
        ("csts-2020", "verified", 700, None, "CSTS-7731"),
        ("whmis", "verified", 1090, 6, None),  # expires next week: amber on Home
        ("first-aid", "self_reported", 300, 795, None),
        ("aerial-platform", "pending", 200, 895, "AWP-55120"),
    ],
    "u-noah": [
        ("cwb-welding", "verified", 400, 330, "CWB-88213"),
        ("csts-2020", "verified", 900, None, None),
        ("fall-protection", "verified", 500, 595, None),
        ("h2s-alive", "self_reported", 100, 995, None),
        ("whmis", "verified", 300, 795, None),
    ],
    "u-ella": [
        ("ab-journeyperson", "verified", 1500, None, "AB-JP-201554"),
        ("csts-2020", "verified", 800, None, None),
        ("fall-protection", "verified", 400, 695, None),
        ("first-aid", "pending", 50, 1045, None),
    ],
    "u-liam": [
        ("telehandler", "verified", 600, 495, None),
        ("forklift", "verified", 600, 495, None),
        ("ground-disturbance", "verified", 300, 795, None),
        ("class-3", "self_reported", 2000, 900, None),
        ("csts-2020", "verified", 1200, None, None),
    ],
    "u-sofia": [
        ("apprentice", "verified", 900, None, "Level 3"),
        ("csts-2020", "self_reported", 400, None, None),
        ("whmis", "self_reported", 400, 695, None),
    ],
    "u-isla": [
        ("csts-2020", "verified", 1000, None, None),
        ("fall-protection", "expired", 1200, -40, None),  # expired: shows red
        ("first-aid", "verified", 600, 495, None),
    ],
    "u-lucas": [
        ("csts-2020", "verified", 600, None, None),
        ("fall-protection", "verified", 300, 795, None),
        ("first-aid", "self_reported", 200, 895, None),
    ],
    "u-amelia": [
        ("forklift", "verified", 500, 595, "FL-B335-9921"),
        ("whmis", "verified", 300, 795, None),
        ("first-aid", "verified", 200, 895, None),
        ("confined-space", "pending", 30, 1065, None),
    ],
}

ORG_WALLETS = {
    "northline": [("cor", "verified", 300, 430), ("wcb-clearance", "verified", 20, 70)],
    "prairie-harvest": [("wcb-clearance", "verified", 40, 50), ("cgl-insurance", "verified", 90, 275)],
    "nisku-fab": [("business-registration", "self_reported", 3000, None)],
    "timberline": [("cor", "verified", 200, 530), ("cgl-insurance", "pending", 30, 335)],
    "liftright": [("wcb-clearance", "self_reported", 10, 80)],
}

# uid -> [(role, company, city, started months ago, ended months ago | None, description)]
HISTORY = {
    "u-maya": [
        ("Electrician", "Riverbend Homes", "Edmonton", 30, 4, "Rough-in and finish on 60+ homes."),
        ("Electrician", "Capital Electric Ltd.", "Edmonton", 70, 31, "Commercial tenant fit-outs."),
        ("Apprentice electrician", "Capital Electric Ltd.", "Edmonton", 110, 71, "Four-year apprenticeship."),
    ],
    "u-noah": [
        ("Structural welder", "Nisku Steel Supply", "Nisku", 40, 2, "Beam and column fabrication."),
        ("Pipe welder", "Northern Spool Co.", "Edmonton", 80, 41, "Pipe spools for upgrader projects."),
    ],
    "u-ella": [
        ("Finish carpenter", "Oak & Line Interiors", "St. Albert", 26, 1, "Trim and stairs."),
        ("Carpenter", "Prairie Framing", "Edmonton", 60, 27, "Framing and forming."),
    ],
    "u-liam": [
        ("Equipment operator", "Ridgeway Earthworks", "Spruce Grove", 50, 3, "Site prep and grading."),
        ("Labourer", "Ridgeway Earthworks", "Spruce Grove", 130, 51, "General site labour."),
        ("Telehandler operator", "Westline Builders", "Edmonton", 20, 12, "Material handling on mid-rise."),
    ],
    "u-sofia": [
        ("Apprentice electrician", "Brightwire Electric", "Edmonton", 30, None, "Residential service."),
        ("Labourer", "Brightwire Electric", "Edmonton", 40, 31, "Site clean-up and material."),
    ],
    "u-isla": [
        ("Concrete finisher", "Solid Ground Concrete", "Sherwood Park", 70, 2, "Flatwork and foundations."),
        ("Labourer", "Solid Ground Concrete", "Sherwood Park", 90, 71, "Forming crew."),
    ],
    "u-lucas": [
        ("Framer", "Timberline Framing Crew", "Sherwood Park", 48, 1, "Production framing."),
        ("Labourer", "Westline Builders", "Edmonton", 60, 49, "General labour."),
    ],
    "u-amelia": [
        ("Forklift operator", "ColdLink Storage", "Leduc", 60, 2, "Reach truck in cold storage."),
        ("Warehouse associate", "Prairie Harvest Foods", "Leduc", 96, 61, "Shipping and receiving."),
        ("Line worker", "Prairie Harvest Foods", "Leduc", 110, 97, "Packaging line."),
    ],
}


def seed_catalog(db: Session) -> None:
    from .catalog import CREDENTIAL_TYPES
    from .market_models import CredentialType

    for tid, name, category, issuer, applies, expiry in CREDENTIAL_TYPES:
        if not db.get(CredentialType, tid):
            db.add(
                CredentialType(
                    id=tid,
                    name=name,
                    category=category,
                    default_issuer=issuer,
                    applies_to=applies,
                    has_expiry=expiry,
                )
            )
    db.flush()


def seed_wallets(db: Session, today: date) -> None:
    from .catalog import CREDENTIAL_TYPES
    from .market_models import Credential, WorkHistory

    issuers = {t[0]: t[3] for t in CREDENTIAL_TYPES}
    for uid, items in WALLETS.items():
        for tid, status, issued_ago, expires_in, number in items:
            db.add(
                Credential(
                    owner_user_id=uid,
                    credential_type_id=tid,
                    issuer=issuers[tid],
                    number=number,
                    issued_on=today - timedelta(days=issued_ago),
                    expires_on=today + timedelta(days=expires_in) if expires_in is not None else None,
                    # "expired" is computed from the date, so store the original status.
                    status="verified" if status == "expired" else status,
                )
            )
    for oid, items in ORG_WALLETS.items():
        for tid, status, issued_ago, expires_in in items:
            db.add(
                Credential(
                    owner_org_id=oid,
                    credential_type_id=tid,
                    issuer=issuers[tid],
                    issued_on=today - timedelta(days=issued_ago),
                    expires_on=today + timedelta(days=expires_in) if expires_in is not None else None,
                    status=status,
                )
            )
    for uid, entries in HISTORY.items():
        for role, company, city, start_ago, end_ago, description in entries:
            db.add(
                WorkHistory(
                    user_id=uid,
                    role=role,
                    company=company,
                    city=city,
                    start_date=today - timedelta(days=30 * start_ago),
                    end_date=today - timedelta(days=30 * end_ago) if end_ago is not None else None,
                    description=description,
                )
            )


def seed_market(db: Session) -> None:
    if db.get(User, "u-maya"):
        return
    today = date.today()
    seed_catalog(db)
    for oid, name, kind, city, industry, about, verification in ORGS:
        org = db.get(Organization, oid) or Organization(id=oid, name=name)
        lat, lng = coordinates(city)
        org.name, org.kind, org.handle, org.city = name, kind, oid, city
        org.lat, org.lng, org.industry, org.about = lat, lng, industry, about
        org.verification_status, org.is_demo = verification, True
        db.add(org)
    db.flush()
    for uid, name, oid, membership in OWNERS:
        kind = next(o[2] for o in ORGS if o[0] == oid)
        db.add(
            User(
                id=uid,
                email=uid.removeprefix("u-") + D,
                full_name=name,
                default_mode=kind,
                onboarded=True,
                membership_id=membership,
            )
        )
        db.flush()
        db.add(OrgMember(org_id=oid, user_id=uid, role="owner"))
    for uid, name, headline, trades, city, radius, rmin, rmax, bio in WORKERS:
        db.add(
            User(
                id=uid,
                email=uid.removeprefix("u-") + D,
                full_name=name,
                default_mode="worker",
                onboarded=True,
            )
        )
        db.flush()
        lat, lng = coordinates(city)
        db.add(
            WorkerProfile(
                user_id=uid,
                handle=uid.removeprefix("u-"),
                headline=headline,
                trades=trades,
                city=city,
                lat=lat,
                lng=lng,
                travel_radius_km=radius,
                rate_min_cents=rmin,
                rate_max_cents=rmax,
                bio=bio,
            )
        )
    db.flush()
    seed_wallets(db, today)
    db.commit()


def demo_orgs_only(db: Session) -> bool:
    return not db.scalar(select(Organization.id).where(Organization.is_demo.is_(False)).limit(1))
