"""Central configuration. All tunable assumptions live here so they are visible."""

# Workplace (destination). Coordinates geocoded from the address below.
# The notebook re-geocodes this live via the routing API and only falls back
# to these values if the lookup fails.
WORKPLACE = {
    "name": "Johnson & Johnson Medical GmbH",
    "address": "Robert-Koch-Strasse 1, 22851 Norderstedt",
    "lat": 53.686952,
    "lon": 10.046418,
}

# Routing API. Free HAFAS wrapper over Deutsche Bahn data, covers HVV.
# No API key required.
API_BASE = "https://v6.db.transport.rest"
API_TIMEOUT = 20          # seconds per request
API_MAX_RETRIES = 4
API_SLEEP = 0.25          # pause between calls to stay under the rate limit

# Target arrival at work, used for every journey query.
# A normal weekday morning gives a realistic commute.
ARRIVAL_WEEKDAY = 0       # 0 = Monday
ARRIVAL_HOUR = 8
ARRIVAL_MINUTE = 30

# Commute-time bins (minutes, door to door).
BIN_EDGES = [30, 45, 60]
BIN_LABELS = ["0-30", "30-45", "45-60", "60+"]

# Deutschlandticket and driving-cost assumptions (for the savings factor).
# Ticket price verified at 63 EUR/month from January 2026.
DTICKET_PRICE_EUR = 63.0
WORK_DAYS_PER_MONTH = 20
DETOUR_FACTOR = 1.3       # road distance vs straight-line distance
CAR_COST_PER_KM_EUR = 0.30  # all-in running cost, German rule of thumb


# Adoption score. A transparent weighted logistic model.
# There is no real adoption ground truth, so these are stated assumptions,
# not learned parameters. Signs reflect direction of influence.

ADOPTION_WEIGHTS = {
    "intercept": 2.6,
    "commute_min": -0.045,     # longer commute lowers adoption
    "n_transfers": -0.45,      # each transfer lowers adoption
    "access_walk_min": -0.04,  # longer walk to the first stop lowers adoption
    "owns_car": -0.80,         # car owners are less likely to switch
    "savings_eur": 0.010,      # money saved vs driving raises adoption
}

POTENTIAL_THRESHOLDS = {"high": 0.60, "medium": 0.35}  # else low

RANDOM_SEED = 42
