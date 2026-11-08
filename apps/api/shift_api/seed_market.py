"""Fictional Shift V1 marketplace fixture (SEED-1 to SEED-4). Never a production seed.

All demo accounts use the reserved @demo.shift.local domain so the local demo sign-in
can list them and the demo reset can recognise them.
"""

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


def seed_market(db: Session) -> None:
    if db.get(User, "u-maya"):
        return
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
    db.commit()


def demo_orgs_only(db: Session) -> bool:
    return not db.scalar(select(Organization.id).where(Organization.is_demo.is_(False)).limit(1))
