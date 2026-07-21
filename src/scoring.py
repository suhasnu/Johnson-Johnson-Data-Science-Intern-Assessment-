# Commute binning and Deutschlandticket adoption scoring

import math

import numpy as np
import pandas as pd

from . import config
from .routing import haversine_km


def bin_commute(minutes):
    edges = config.BIN_EDGES
    labels = config.BIN_LABELS
    if minutes <= edges[0]:
        return labels[0]
    if minutes <= edges[1]:
        return labels[1]
    if minutes <= edges[2]:
        return labels[2]
    return labels[3]


def monthly_driving_cost(from_lat, from_lon, to_lat, to_lon):
    # Estimated monthly car running cost for this commute!
    road_km = haversine_km(from_lat, from_lon, to_lat, to_lon) * config.DETOUR_FACTOR
    monthly_km = road_km * 2 * config.WORK_DAYS_PER_MONTH
    return monthly_km * config.CAR_COST_PER_KM_EUR


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def adoption_score(commute_min, n_transfers, access_walk_min, owns_car, savings_eur):
    w = config.ADOPTION_WEIGHTS
    u = (
        w["intercept"]
        + w["commute_min"] * commute_min
        + w["n_transfers"] * n_transfers
        + w["access_walk_min"] * access_walk_min
        + w["owns_car"] * owns_car
        + w["savings_eur"] * savings_eur
    )
    return _sigmoid(u)


def potential_label(score):
    t = config.POTENTIAL_THRESHOLDS
    if score >= t["high"]:
        return "High"
    if score >= t["medium"]:
        return "Medium"
    return "Low"


def enrich(df, workplace):
    """Add savings, adoption score, potential label and commute bin to df.

    Expects df to already contain commute_min, n_transfers, access_walk_min.
    """
    df = df.copy()
    df["driving_cost_eur"] = df.apply(
        lambda r: monthly_driving_cost(
            r["home_lat"], r["home_lon"], workplace["lat"], workplace["lon"]
        ),
        axis=1,
    ).round(1)
    df["savings_eur"] = (df["driving_cost_eur"] - config.DTICKET_PRICE_EUR).round(1)

    df["adoption_score"] = df.apply(
        lambda r: adoption_score(
            r["commute_min"],
            r["n_transfers"],
            r["access_walk_min"],
            r["owns_car"],
            r["savings_eur"],
        ),
        axis=1,
    ).round(3)

    df["potential"] = df["adoption_score"].apply(potential_label)
    df["commute_bin"] = df["commute_min"].apply(bin_commute)
    return df


def bin_summary(df):
    # Per-bin counts and percentages, plus cumulative within-time shares!
    counts = df["commute_bin"].value_counts().reindex(config.BIN_LABELS, fill_value=0)
    pct = (counts / len(df) * 100).round(1)
    within_30 = round((df["commute_min"] <= 30).mean() * 100, 1)
    within_45 = round((df["commute_min"] <= 45).mean() * 100, 1)
    within_60 = round((df["commute_min"] <= 60).mean() * 100, 1)
    over_60 = round((df["commute_min"] > 60).mean() * 100, 1)
    return {
        "per_bin_pct": pct.to_dict(),
        "within_30_pct": within_30,
        "within_45_pct": within_45,
        "within_60_pct": within_60,
        "over_60_pct": over_60,
    }


def area_summary(df):
    # Mean commute and adoption per residential area, sorted by commute!
    g = (
        df.groupby("area")
        .agg(
            employees=("employee_id", "count"),
            mean_commute_min=("commute_min", "mean"),
            mean_adoption=("adoption_score", "mean"),
            high_potential=("potential", lambda s: (s == "High").sum()),
        )
        .round({"mean_commute_min": 1, "mean_adoption": 3})
        .sort_values("mean_commute_min")
    )
    return g


def key_factors(df):
    # Correlation of each driver with the adoption score, for the summary!
    cols = ["commute_min", "n_transfers", "access_walk_min", "owns_car", "savings_eur"]
    corr = df[cols + ["adoption_score"]].corr()["adoption_score"].drop("adoption_score")
    return corr.round(3).sort_values()
