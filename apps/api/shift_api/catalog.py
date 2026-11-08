"""Reference data for the V1 marketplace: trades, places and schedule patterns."""

from math import asin, cos, radians, sin, sqrt

TRADES = [
    "Carpentry",
    "Framing",
    "Electrical",
    "Plumbing",
    "Welding",
    "Pipefitting",
    "Millwright",
    "Heavy equipment",
    "Forklift & warehouse",
    "Food processing",
    "Concrete",
    "General labour",
]

INDUSTRIES = [
    "Residential construction",
    "Commercial construction",
    "Industrial construction",
    "Manufacturing",
    "Food processing",
    "Oil and gas",
    "Warehousing and logistics",
    "Staffing",
]

# Alberta places used for distance matching (approximate city centres).
CITIES: dict[str, tuple[float, float]] = {
    "Edmonton": (53.5461, -113.4938),
    "Sherwood Park": (53.5413, -113.2958),
    "St. Albert": (53.6305, -113.6256),
    "Spruce Grove": (53.5450, -113.9008),
    "Leduc": (53.2594, -113.5492),
    "Nisku": (53.3397, -113.5276),
    "Fort Saskatchewan": (53.7128, -113.2130),
    "Red Deer": (52.2690, -113.8116),
    "Calgary": (51.0447, -114.0719),
    "Airdrie": (51.2917, -114.0144),
    "Lethbridge": (49.6956, -112.8451),
    "Grande Prairie": (55.1707, -118.7947),
    "Fort McMurray": (56.7268, -111.3790),
}

SCHEDULE_PATTERNS = {
    "mon_fri": "Mon–Fri, days",
    "nights": "Mon–Fri, nights",
    "four_on_four_off": "4 on, 4 off",
    "weekends": "Weekends only",
}


# Plain-language starting points for a posting description, by trade (POST-1).
TEMPLATES = {
    "Electrical": "We need a journeyperson electrician for rough-in, wiring and device "
    "finishing. You'll read prints, work to the CEC and coordinate with other trades on site.",
    "Carpentry": "We need a carpenter for framing, trim and finishing work. Bring your own "
    "hand tools; power tools and materials are on site.",
    "Framing": "We need framers for walls, floors and roof systems on production homes. "
    "Crews work from plans with a lead hand on site.",
    "Plumbing": "We need a plumber for rough-in and finishing, including DWV, water lines "
    "and fixture setting.",
    "Welding": "We need a welder for structural and pipe work in our shop. Work is to "
    "drawing with QC sign-off on every joint.",
    "Pipefitting": "We need a pipefitter to fabricate and install process piping from "
    "isometric drawings.",
    "Millwright": "We need a millwright for equipment installation, alignment and "
    "maintenance during the work window.",
    "Heavy equipment": "We need an equipment operator for site work. Machines are "
    "maintained and fuelled by us.",
    "Forklift & warehouse": "We need forklift operators to load, unload and move "
    "product safely through the warehouse.",
    "Food processing": "We need production workers for our processing lines. "
    "Food-safety training is provided on day one.",
    "Concrete": "We need concrete workers for forming, placing and finishing.",
    "General labour": "We need general labourers for site clean-up, material handling "
    "and helping the trades.",
}

ACSA = "Alberta Construction Safety Association"
# (id, name, category, default issuer, applies_to, has_expiry) — seeded into
# credential_types; the catalog is data and can grow without code changes.
CREDENTIAL_TYPES = [
    ("red-seal", "Red Seal endorsement", "Trade", "Red Seal Program", "worker", False),
    (
        "ab-journeyperson",
        "Alberta journeyperson certificate",
        "Trade",
        "Alberta Apprenticeship and Industry Training",
        "worker",
        False,
    ),
    (
        "apprentice",
        "Apprentice level (1–4)",
        "Trade",
        "Alberta Apprenticeship and Industry Training",
        "worker",
        False,
    ),
    ("csts-2020", "CSTS-2020", "Safety", ACSA, "worker", False),
    ("fall-protection", "Fall Protection", "Safety", ACSA, "worker", True),
    ("whmis", "WHMIS", "Safety", "Training provider", "worker", True),
    ("first-aid", "Standard First Aid & CPR", "Safety", "Canadian Red Cross", "worker", True),
    ("h2s-alive", "H2S Alive", "Safety", "Energy Safety Canada", "worker", True),
    ("confined-space", "Confined Space", "Safety", "Training provider", "worker", True),
    ("ground-disturbance", "Ground Disturbance", "Safety", "Training provider", "worker", True),
    (
        "forklift",
        "Forklift operator (CSA B335 training)",
        "Equipment",
        "Training provider",
        "worker",
        True,
    ),
    ("aerial-platform", "Aerial work platform", "Equipment", "Training provider", "worker", True),
    ("telehandler", "Telehandler", "Equipment", "Training provider", "worker", True),
    ("rigging", "Rigging / signalperson", "Equipment", "Training provider", "worker", True),
    ("cwb-welding", "CWB welding certification", "Trade", "Canadian Welding Bureau", "worker", True),
    ("class-1", "Class 1 licence", "Driving", "Alberta Registries", "worker", True),
    ("class-3", "Class 3 licence", "Driving", "Alberta Registries", "worker", True),
    ("air-brake", "Air brake endorsement", "Driving", "Alberta Registries", "worker", False),
    (
        "business-registration",
        "Business registration",
        "Business",
        "Alberta Corporate Registry",
        "org",
        False,
    ),
    ("trade-licence", "Trade licence held", "Business", "Alberta Municipal Affairs", "org", True),
    ("cor", "COR (Certificate of Recognition)", "Safety", ACSA, "org", True),
    ("wcb-clearance", "WCB-Alberta clearance letter", "Safety", "WCB-Alberta", "org", True),
    ("equipment-fleet", "Equipment fleet list", "Equipment", "Self-declared", "org", False),
    ("auto-insurance", "Commercial auto insurance", "Driving", "Insurer", "org", True),
    (
        "cgl-insurance",
        "Commercial general liability insurance",
        "Business",
        "Insurer",
        "org",
        True,
    ),
    (
        "prequal",
        "Contractor prequalification (ISNetworld, ComplyWorks)",
        "Business",
        "Prequalification service",
        "org",
        True,
    ),
]
CATEGORIES = ["Trade", "Safety", "Equipment", "Driving", "Business", "Other"]


def coordinates(city: str | None) -> tuple[float | None, float | None]:
    if city and city in CITIES:
        return CITIES[city]
    return None, None


def distance_km(a_lat, a_lng, b_lat, b_lng) -> float | None:
    """Great-circle distance; None when either point is unknown."""
    if None in (a_lat, a_lng, b_lat, b_lng):
        return None
    dlat, dlng = radians(b_lat - a_lat), radians(b_lng - a_lng)
    h = sin(dlat / 2) ** 2 + cos(radians(a_lat)) * cos(radians(b_lat)) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))
