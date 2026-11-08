"""For You ranking weights and windows (FEED-2). Tune here; nothing else hard-codes them."""

WEIGHTS = {
    "trade_match": 40,  # posting trade is one of the worker's trades
    "within_radius": 20,  # scaled: full points at 0 km, 0 at the edge of the travel radius
    "starts_soon": 15,  # starts within STARTS_SOON_DAYS
    "new_posting": 15,  # posted within NEW_POSTING_HOURS
    "nice_to_haves": 10,  # worker holds every nice-to-have credential (if any are listed)
}
STARTS_SOON_DAYS = 30
NEW_POSTING_HOURS = 48
NEW_SINCE_HOURS = 24  # "New since yesterday"
EXPIRING_SOON_DAYS = 30  # amber warning on Home (CRED-2)
