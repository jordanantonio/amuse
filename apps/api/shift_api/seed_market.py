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
    # v2 demo personas (DEMO-1): the team members who present the demo.
    ("u-rahul", "Rahul Ghosh", "prairie-harvest", None),
    ("u-jordan", "Jordan Antonio", "timberline", None),
]

WORKERS = [
    # user id, name, headline, trades, city, radius km, rate min, rate max, bio
    (
        "u-tyler",
        "Tyler Brandt",
        "Warehouse worker",
        ["Forklift & warehouse", "General labour"],
        "Red Deer",
        30,
        2200,
        2800,
        "Looking for steady warehouse hours.",
    ),
    (
        "u-ilya",
        "Ilya Sukhanov",
        "General labourer · 4 yrs in food processing & construction",
        ["General labour", "Food processing", "Forklift & warehouse"],
        "Nisku",
        25,
        2400,
        3000,
        "I’m the person crews call when a night shift needs to run clean. Four years between "
        "a Leduc packing plant and residential sites taught me to keep a station spotless, "
        "move product safely on a forklift and look out for the new guy. I like early starts, "
        "clear checklists and finishing a shutdown ahead of schedule. Proudest moment: zero "
        "recordables across a 14-night sanitation shutdown.",
    ),
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
        "Third-year apprentice looking for hours toward my journeyperson certification.",
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
    "u-tyler": [
        ("whmis", "verified", 300, 795, None),
        ("first-aid", "self_reported", 100, 995, None),
    ],
    "u-ilya": [
        ("whmis", "verified", 1090, 6, "WHMIS-20931"),  # expires next week: amber on Home
        ("first-aid", "verified", 400, 695, "SFA-77120"),
        ("csts-2020", "verified", 800, None, "CSTS-55218"),
        ("forklift", "verified", 500, 595, "FL-B335-4410"),
        ("confined-space", "pending", 40, 1055, None),
    ],
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
    "u-tyler": [
        ("Warehouse associate", "Red Deer Distribution", "Red Deer", 14, 1, "Picking and packing."),
        ("Labourer", "Central Alberta Builders", "Red Deer", 30, 15, "Site clean-up."),
    ],
    "u-ilya": [
        ("Sanitation lead hand", "Prairie Harvest Foods", "Leduc", 20, 2,
         "Ran the overnight sanitation crew of six across two production lines."),
        ("General labourer", "Westline Builders", "Edmonton", 34, 21,
         "Site clean-up, material handling and framing support on mid-rise builds."),
        ("Forklift operator", "ColdLink Storage", "Leduc", 48, 35,
         "Loaded and staged pallets in a -20 °C freezer warehouse."),
    ],
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


R = True  # required
N = False  # nice-to-have
# id, org, title, trade, type, city, site address, start (days from today), end,
# pattern, exclusive, pay cents, unit, headcount, status, posted hours ago,
# [(credential type, required, must be verified)]
POSTINGS = [
    ("p-rough-in", "northline", "Electrical rough-in, 4-plex", "Electrical", "individual",
     "Edmonton", "11820 87 St NW, Edmonton", 14, 180, "mon_fri", True, 4800, "hour", 2, "open", 20,
     [("ab-journeyperson", R, True), ("csts-2020", R, False), ("whmis", R, False), ("first-aid", N, False)]),
    ("p-finish-carp", "northline", "Finish carpenter, show homes", "Carpentry", "individual",
     "Edmonton", "4210 Allard Way SW, Edmonton", 21, 90, "mon_fri", True, 4000, "hour", 2, "open", 70,
     [("csts-2020", R, False), ("fall-protection", R, False)]),
    ("p-site-labour", "northline", "Site labourer, spring framing", "General labour", "individual",
     "Edmonton", None, 40, 70, "mon_fri", False, 2800, "hour", 4, "open", 30,
     [("csts-2020", R, False), ("fall-protection", R, False)]),
    ("p-service-elec", "northline", "Service electrician, warranty calls", "Electrical", "individual",
     "Sherwood Park", None, 60, 240, "mon_fri", False, 4400, "hour", 1, "open", 100,
     [("ab-journeyperson", R, False), ("csts-2020", R, False)]),
    ("p-temp-power", "northline", "Temporary power and lighting", "Electrical", "individual",
     "St. Albert", "25 Erin Ridge Rd, St. Albert", 10, 40, "mon_fri", False, 4700, "hour", 2, "open", 6,
     [("ab-journeyperson", R, False), ("csts-2020", R, False), ("whmis", R, False)]),
    ("p-high-bay", "northline", "Aerial lift electrician, high-bay warehouse", "Electrical", "individual",
     "Calgary", None, 90, 120, "mon_fri", True, 5200, "hour", 1, "open", 140,
     [("ab-journeyperson", R, False), ("aerial-platform", R, True)]),
    ("p-maint-elec", "prairie-harvest", "Maintenance electrician, night shift", "Electrical", "individual",
     "Leduc", "6505 Sparrow Dr, Leduc", 7, 120, "nights", True, 5200, "hour", 1, "open", 160,
     [("ab-journeyperson", R, False), ("whmis", R, False), ("first-aid", N, False), ("confined-space", N, False)]),
    ("p-forklift", "prairie-harvest", "Forklift operator, cold storage", "Forklift & warehouse", "individual",
     "Leduc", None, 5, 60, "four_on_four_off", False, 2700, "hour", 3, "open", 50,
     [("forklift", R, True), ("whmis", R, False)]),
    ("p-pack-lead", "prairie-harvest", "Packaging line lead, weekends", "Food processing", "individual",
     "Leduc", None, 10, 100, "weekends", False, 3000, "hour", 1, "open", 120,
     [("whmis", R, False), ("first-aid", R, False)]),
    ("p-sanitation", "prairie-harvest", "General Labourer — Sanitation Crew", "General labour", "individual",
     "Leduc", "6505 Sparrow Dr, Leduc", 12, 54, "nights", False, 2600, "hour", 4, "open", 20,
     [("whmis", R, False), ("first-aid", R, False), ("csts-2020", R, False), ("forklift", N, False, "valuable")]),
    # Ilya's prepared state (DEMO-4): five more eligible contracts and a waiting offer.
    ("p-production-nights", "prairie-harvest", "Production line operator, nights", "Food processing",
     "individual", "Leduc", "6505 Sparrow Dr, Leduc", 7, 120, "nights", True, 2900, "hour", 1, "open", 150,
     [("whmis", R, False), ("first-aid", R, False)]),
    ("p-food-line", "prairie-harvest", "Food production worker, line 1", "Food processing", "individual",
     "Leduc", None, 21, 90, "mon_fri", False, 2500, "hour", 3, "open", 60,
     [("whmis", R, False), ("first-aid", R, False)]),
    ("p-shop-labour", "nisku-fab", "Shop labourer, steel yard", "General labour", "individual",
     "Nisku", "1004 8 St, Nisku", 14, 70, "mon_fri", False, 2700, "hour", 2, "open", 30,
     [("csts-2020", R, False), ("whmis", R, False)]),
    ("p-yard-forklift", "nisku-fab", "Yard forklift operator", "Forklift & warehouse", "individual",
     "Nisku", None, 28, 85, "mon_fri", False, 2850, "hour", 1, "open", 80,
     [("forklift", R, True), ("csts-2020", R, False)]),
    ("p-cleanup", "northline", "Site clean-up crew, 4-plex", "General labour", "individual",
     "Edmonton", None, 35, 65, "mon_fri", False, 2600, "hour", 3, "open", 110,
     [("csts-2020", R, False)]),
    ("p-line2", "prairie-harvest", "Electrician, line 2 upgrade", "Electrical", "individual",
     "Leduc", None, 50, 80, "mon_fri", False, 5000, "hour", 1, "open", 90,
     [("ab-journeyperson", R, False), ("whmis", R, False), ("csts-2020", R, False)]),
    ("p-welder", "nisku-fab", "Structural welder, pipe spool shop", "Welding", "individual",
     "Nisku", "1004 8 St, Nisku", 3, 150, "mon_fri", True, 4600, "hour", 3, "open", 200,
     [("cwb-welding", R, True), ("csts-2020", R, False)]),
    ("p-panel", "nisku-fab", "Shop electrician, panel builds", "Electrical", "individual",
     "Nisku", None, 30, 75, "mon_fri", False, 4500, "hour", 1, "open", 72,
     [("ab-journeyperson", R, False), ("csts-2020", R, False)]),
    ("p-millwright", "nisku-fab", "Millwright, shutdown support", "Millwright", "individual",
     "Nisku", None, 45, 59, "four_on_four_off", True, 5800, "hour", 2, "open", 30,
     [("ab-journeyperson", R, True), ("h2s-alive", R, False)]),
    ("p-apprentice", "nisku-fab", "Electrical apprentice (level 3+)", "Electrical", "individual",
     "Nisku", None, 20, 110, "mon_fri", True, 3200, "hour", 1, "open", 40,
     [("apprentice", R, False), ("csts-2020", N, False)]),
    ("p-warehouse", "prairie-harvest", "Warehouse associate, shipping dock", "Forklift & warehouse",
     "individual", "Leduc", "6505 Sparrow Dr, Leduc", 18, 110, "mon_fri", True, 2700, "hour", 3, "open", 50,
     [("whmis", R, False), ("forklift", N, False, "valuable"), ("first-aid", N, False, "nice")]),
    ("a-shutdown", "prairie-harvest", "Shutdown crew: 8 forklift operators", "Forklift & warehouse", "agency",
     "Leduc", "6505 Sparrow Dr, Leduc", 25, 35, "four_on_four_off", True, 3400, "hour", 8, "open", 30,
     [("wcb-clearance", R, False), ("cgl-insurance", N, False)]),
    ("a-framing", "northline", "Framing crew for a 12-home phase", "Framing", "agency",
     "Edmonton", None, 30, 150, "mon_fri", True, 3800, "hour", 6, "open", 60,
     [("cor", R, False), ("cgl-insurance", R, False)]),
    # History: contracts that already ran, for Active / Past and "Completed on Shift".
    ("p-upgrade", "northline", "Electrical service upgrade, 2 homes", "Electrical", "individual",
     "Edmonton", "9640 76 Ave NW, Edmonton", -90, -40, "mon_fri", True, 4600, "hour", 1, "filled", 2600,
     [("ab-journeyperson", R, False)]),
    ("p-trim", "northline", "Trim carpenter, model suite", "Carpentry", "individual",
     "Edmonton", "7731 Ellerslie Rd SW, Edmonton", -10, 20, "mon_fri", True, 3900, "hour", 1, "filled", 600,
     [("csts-2020", R, False)]),
    ("p-welder-done", "nisku-fab", "Welder, tank repair", "Welding", "individual",
     "Nisku", None, -1, 13, "mon_fri", False, 4500, "hour", 1, "filled", 400,
     [("cwb-welding", R, False)]),
]

# posting, applicant (user id or org id), status, note, hours ago
APPLICATIONS = [
    ("p-warehouse", "u-amelia", "accepted", "", 300),
    ("p-warehouse", "u-ilya", "applied", "Forklift-certified and can start early.", 30),
    ("p-warehouse", "u-noah", "applied", "Happy to learn the dock.", 22),
    ("p-warehouse", "u-sofia", "shortlisted", "", 40),
    ("p-warehouse", "u-tyler", "applied", "", 3),
    ("p-warehouse", "u-liam", "applied", "Cold storage experience.", 60),
    ("p-warehouse", "u-lucas", "applied", "", 44),
    ("p-production-nights", "u-ilya", "offered", "Four years on night sanitation in Leduc.", 70),
    ("p-pack-lead", "u-ilya", "applied", "Happy to cover weekends between contracts.", 26),
    ("p-maint-elec", "u-maya", "offered", "Nine years on residential and light industrial.", 60),
    ("p-pack-lead", "u-maya", "applied", "Happy to cover weekends between contracts.", 30),
    ("p-finish-carp", "u-ella", "applied", "Trim and stairs are my specialty.", 5),
    ("p-finish-carp", "u-lucas", "shortlisted", "Available from the start date.", 40),
    ("p-finish-carp", "u-noah", "applied", "Shop carpentry experience too.", 20),
    ("p-forklift", "u-amelia", "applied", "Eight years on reach trucks in cold storage.", 12),
    ("p-apprentice", "u-sofia", "shortlisted", "Third-year apprentice, need hours.", 30),
    ("a-framing", "timberline", "applied", "Six framers and a lead hand available.", 25),
    ("p-upgrade", "u-maya", "completed", "", 2500),
    ("p-trim", "u-ella", "accepted", "", 500),
    ("p-welder-done", "u-noah", "accepted", "", 300),
]


# Full apply-flow content for the demo posting (APPLY-1); others use sensible defaults.
POSTING_CONTENT = {
    "p-sanitation": {
        "shift_hours": "10 PM – 6 AM, Mon–Fri (8 h with a paid 30-minute break)",
        "ppe_provided": ["Hairnet and beard net", "Chemical-resistant gloves", "Face shield", "Rubber apron"],
        "ppe_required": ["CSA steel-toe rubber boots"],
        "typical_day": (
            "Start with a 10-minute crew huddle and a lock-out check with the lead hand. Break "
            "down and foam the two packaging lines, rinse, sanitize, then swab surfaces for the "
            "QA team before the 6 AM restart. You're on your feet in a wet, cool (6 °C) room, "
            "with a hot meal break at 2 AM."
        ),
        "questions": [
            {"id": "overnight", "prompt": "Comfortable with overnight shifts?", "kind": "yes_no"},
            {"id": "boots", "prompt": "Do you have CSA steel-toe boots?", "kind": "yes_no"},
            {"id": "start", "prompt": "Earliest start date", "kind": "date"},
        ],
    },
    "p-warehouse": {
        "shift_hours": "7 AM – 3:30 PM, Mon–Fri",
        "ppe_provided": ["Hi-vis vest", "Cut-resistant gloves"],
        "ppe_required": ["CSA steel-toe boots"],
        "typical_day": "Stage outbound pallets, load trailers on the shipping dock and keep the dock clear for the forklift crew.",
        "questions": [
            {"id": "lift", "prompt": "Comfortable lifting 50 lb all shift?", "kind": "yes_no"},
            {"id": "start", "prompt": "Earliest start date", "kind": "date"},
        ],
        "coverage": [
            {"credential_type_id": "forklift", "needed": 2},
            {"credential_type_id": "first-aid", "needed": 1},
        ],
    },
    "p-forklift": {
        "shift_hours": "6 AM – 6 PM on a 4-on, 4-off rotation",
        "ppe_provided": ["Insulated freezer suit", "Hi-vis vest"],
        "ppe_required": ["CSA steel-toe boots"],
        "questions": [
            {"id": "cold", "prompt": "Comfortable working in -20 °C for an hour at a time?", "kind": "yes_no"},
            {"id": "start", "prompt": "Earliest start date", "kind": "date"},
        ],
    },
}


# Screening answers (posting, applicant) -> answers. Tyler skipped them (RANK-4 signal).
ANSWERS = {
    ("p-warehouse", "u-ilya"): {"lift": "Yes", "start": "earliest"},
    ("p-warehouse", "u-noah"): {"lift": "Yes"},
    ("p-warehouse", "u-sofia"): {"lift": "Yes", "start": "earliest"},
    ("p-warehouse", "u-liam"): {"lift": "Yes"},
    ("p-warehouse", "u-lucas"): {"lift": "No"},
}
# Tyler sent 10 more applications in about three minutes.
BURST = ["p-cleanup", "p-food-line", "p-shop-labour", "p-site-labour", "p-forklift", "p-pack-lead",
         "p-yard-forklift", "p-sanitation", "p-temp-power", "p-service-elec"]


def seed_postings(db: Session, today: date) -> None:
    from datetime import datetime, timezone
    from .engagements import book
    from .market_models import ContractApplication, Posting, PostingRequirement, WorkHistory

    now = datetime.now(timezone.utc)
    for (pid, oid, title, trade, ptype, city, address, s, e, pattern, excl, pay, unit, head,
         status, hours, reqs) in POSTINGS:
        lat, lng = coordinates(city)
        from .catalog import TEMPLATES

        db.add(
            Posting(
                id=pid, org_id=oid, title=title, trade=trade, posting_type=ptype,
                description=TEMPLATES.get(trade, ""), city=city, lat=lat, lng=lng,
                site_address=address, start_date=today + timedelta(days=s),
                end_date=today + timedelta(days=e), schedule_pattern=pattern, is_exclusive=excl,
                pay_rate_cents=pay, pay_unit=unit, headcount=head, status=status,
                created_at=now - timedelta(hours=hours),
                **POSTING_CONTENT.get(pid, {}),
            )
        )
        db.flush()
        for tid, required, verified, *weight in reqs:
            db.add(PostingRequirement(posting_id=pid, credential_type_id=tid,
                                      required=required, must_be_verified=verified,
                                      weight=None if required else (weight[0] if weight else "nice")))
    db.flush()
    burst_start = now - timedelta(hours=3)
    for i, pid in enumerate(BURST):
        at = burst_start + timedelta(seconds=20 * i)
        db.add(ContractApplication(posting_id=pid, applicant_user_id="u-tyler", status="applied",
                                   created_at=at, updated_at=at, answers={}))
    for pid, who, status, note, hours in APPLICATIONS:
        owner = {"applicant_user_id": who} if who.startswith("u-") else {"applicant_org_id": who}
        at = now - timedelta(hours=hours)
        answers = dict(ANSWERS.get((pid, who), {}))
        if answers.get("start") == "earliest":
            answers["start"] = str(today + timedelta(days=18))
        a = ContractApplication(posting_id=pid, status=status, note=note, created_at=at,
                                updated_at=at, answers=answers, **owner)
        db.add(a)
        db.flush()
        if status in {"accepted", "completed"}:
            posting = db.get(Posting, pid)
            e = book(db, a, posting, "completed" if status == "completed" else "active")
            if status == "completed":
                org = db.get(Organization, posting.org_id)
                db.add(WorkHistory(
                    user_id=who, role=posting.title, company=org.name, city=posting.city,
                    start_date=posting.start_date, end_date=posting.end_date,
                    description="Completed on Shift.", engagement_id=e.id,
                ))


H = 60  # minutes per hour
DAYS = range(0, 5)  # Mon-Fri
# Weekly availability windows: uid -> [(weekdays, start minute, end minute)]
WORKER_HOURS = {
    "u-amelia": [(DAYS, 6 * H, 18 * H), ([5], 6 * H, 14 * H)],
    "u-ilya": [(DAYS, 6 * H, 18 * H)],
    "u-isla": [(DAYS, 7 * H, 17 * H)],
    "u-noah": [(range(0, 4), 20 * H, 31 * H)],  # nights, 8 PM-7 AM
    "u-sofia": [(DAYS, 8 * H, 17 * H)],
    "u-lucas": [(DAYS, 7 * H, 16 * H)],
    "u-liam": [(range(0, 7), 5 * H, 15 * H)],  # not on the crew: the marketplace backup
    "u-maya": [(DAYS, 8 * H, 17 * H)],
    "u-ella": [(DAYS, 8 * H, 17 * H)],
}
CREW = {"prairie-harvest": ["u-amelia", "u-ilya", "u-isla", "u-noah", "u-sofia", "u-lucas"]}
# (weekdays, label, start, end, needed, preferred cert, required certs)
SLOT_PLAN = [
    (DAYS, "Packaging line", 8 * H, 12 * H, 2, "forklift", []),
    (DAYS, "Packaging line", 12 * H + 30, 16 * H + 30, 2, None, []),
    (range(0, 4), "Sanitation", 22 * H, 30 * H, 1, None, ["whmis"]),
    ([0, 2, 4, 5], "Loading dock", 6 * H, 14 * H, 1, None, ["forklift"]),
    ([6], "Cold storage restock", 6 * H, 14 * H, 1, None, ["forklift"]),
]
# Pre-filled spots this week: (weekday, label, start, uid)
PREFILLED = [
    (0, "Packaging line", 8 * H, "u-amelia"),
    (0, "Packaging line", 8 * H, "u-sofia"),
    (0, "Packaging line", 12 * H + 30, "u-isla"),
    (0, "Packaging line", 12 * H + 30, "u-ilya"),
    (1, "Packaging line", 8 * H, "u-ilya"),
    (0, "Sanitation", 22 * H, "u-noah"),
]


def seed_crew(db: Session, today: date) -> None:
    from .market_models import CrewAssignment, CrewMember, CrewRules, CrewSlot, WorkerHours

    for uid, windows in WORKER_HOURS.items():
        for weekdays, start, end in windows:
            for wd in weekdays:
                db.add(WorkerHours(user_id=uid, weekday=wd, start_minute=start, end_minute=end))
    for oid, members in CREW.items():
        db.add(CrewRules(org_id=oid, max_consecutive_days=5, min_rest_hours=10, max_weekly_hours=40))
        for uid in members:
            db.add(CrewMember(org_id=oid, user_id=uid))
    monday = today - timedelta(days=today.weekday())
    created: dict[tuple, str] = {}
    for week in (0, 1):
        for weekdays, label, start, end, needed, preferred, required in SLOT_PLAN:
            for wd in weekdays:
                slot = CrewSlot(
                    org_id="prairie-harvest",
                    day=monday + timedelta(days=7 * week + wd),
                    start_minute=start,
                    end_minute=end,
                    label=label,
                    needed=needed,
                    preferred_cert=preferred,
                    required_certs=required,
                )
                db.add(slot)
                db.flush()
                if week == 0:
                    created[(wd, label, start)] = slot.id
    seen: dict[str, int] = {}
    for wd, label, start, uid in PREFILLED:
        sid = created[(wd, label, start)]
        if seen.get(sid, 0) >= 2:
            continue
        seen[sid] = seen.get(sid, 0) + 1
        db.add(CrewAssignment(slot_id=sid, user_id=uid, status="assigned"))


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
    db.flush()
    seed_postings(db, today)
    db.flush()
    seed_crew(db, today)
    db.commit()


def demo_orgs_only(db: Session) -> bool:
    return not db.scalar(select(Organization.id).where(Organization.is_demo.is_(False)).limit(1))
