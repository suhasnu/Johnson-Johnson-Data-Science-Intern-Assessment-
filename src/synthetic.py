"""Synthetic employee generation.

No real employee data is used. Homes are sampled around residential centres in
Hamburg and the surrounding towns, with a population-style weighting so the
distribution looks realistic. Each home gets a small random offset from its
centre.
"""

import numpy as np
import pandas as pd

# Residential anchors: (name, lat, lon, weight, spread_km).
# Weight approximates relative population. Spread controls how far homes
# scatter from the centre.
ANCHORS = [
    ("Hamburg-Mitte",     53.5503,  9.9937, 10, 2.5),
    ("Altona",            53.5500,  9.9350,  9, 2.2),
    ("Eimsbuettel",       53.5750,  9.9530,  9, 2.0),
    ("Winterhude",        53.5960,  9.9990,  7, 1.8),
    ("Barmbek",           53.5870, 10.0430,  7, 1.8),
    ("Wandsbek",          53.5820, 10.0900,  8, 2.2),
    ("Harburg",           53.4600,  9.9830,  8, 2.5),
    ("Bergedorf",         53.4890, 10.2130,  6, 2.5),
    ("Norderstedt",       53.7060,  9.9930,  6, 2.0),
    ("Ahrensburg",        53.6740, 10.2410,  4, 1.8),
    ("Pinneberg",         53.6560,  9.7990,  4, 1.8),
    ("Wedel",             53.5830,  9.7080,  3, 1.5),
    ("Quickborn",         53.7280,  9.9080,  3, 1.5),
    ("Henstedt-Ulzburg",  53.7930,  9.9760,  3, 1.6),
    ("Reinbek",           53.5150, 10.2490,  3, 1.5),
    ("Buxtehude",         53.4760,  9.7000,  3, 1.6),
    ("Elmshorn",          53.7530,  9.6530,  3, 1.7),
    ("Geesthacht",        53.4360, 10.3760,  2, 1.6),
    ("Stade",             53.5940,  9.4760,  2, 1.7),
    ("Lueneburg",         53.2500, 10.4140,  2, 2.0),
]

# 1 degree latitude is about 111 km. Longitude scales by cos(latitude).
_KM_PER_DEG_LAT = 111.0


def _km_per_deg_lon(lat):
    return 111.320 * np.cos(np.radians(lat))


def generate_employees(n=200, seed=42):
    # Return a DataFrame of n synthetic employees!
    rng = np.random.default_rng(seed)

    names = [a[0] for a in ANCHORS]
    lats = np.array([a[1] for a in ANCHORS])
    lons = np.array([a[2] for a in ANCHORS])
    weights = np.array([a[3] for a in ANCHORS], dtype=float)
    spreads = np.array([a[4] for a in ANCHORS])
    probs = weights / weights.sum()

    idx = rng.choice(len(ANCHORS), size=n, p=probs)

    home_lat = np.empty(n)
    home_lon = np.empty(n)
    for i, a in enumerate(idx):
        sigma_km = spreads[a]
        dlat = rng.normal(0, sigma_km / _KM_PER_DEG_LAT)
        dlon = rng.normal(0, sigma_km / _km_per_deg_lon(lats[a]))
        home_lat[i] = lats[a] + dlat
        home_lon[i] = lons[a] + dlon

    age = rng.normal(41, 11, size=n).clip(20, 64).round().astype(int)

    # Car ownership rises with distance from the Hamburg core.
    core_lat, core_lon = 53.5503, 9.9937
    dist_core = np.hypot(
        (home_lat - core_lat) * _KM_PER_DEG_LAT,
        (home_lon - core_lon) * _km_per_deg_lon(core_lat),
    )
    car_prob = np.clip(0.30 + 0.03 * dist_core, 0.30, 0.85)
    owns_car = (rng.random(n) < car_prob).astype(int)

    df = pd.DataFrame(
        {
            "employee_id": [f"E{1000 + i}" for i in range(n)],
            "area": [names[a] for a in idx],
            "home_lat": home_lat.round(6),
            "home_lon": home_lon.round(6),
            "age": age,
            "owns_car": owns_car,
        }
    )
    return df
