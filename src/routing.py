# Public transport routing.

import json
import math
import os
import time
from datetime import datetime, timedelta, timezone

import requests

from . import config

_CACHE_PATH = os.path.join("data", "cache", "commute_cache.json")
_cache = None
_session = None


# Small helpers
def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(
            {"User-Agent": "dticket-commute-analysis (assessment project)"}
        )
    return _session


def _load_cache():
    global _cache
    if _cache is None:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        else:
            _cache = {}
    return _cache


def save_cache():
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(_load_cache(), f)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def next_arrival_iso():
    """ISO timestamp for the next configured weekday and time, Europe/Berlin."""
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Europe/Berlin")
    except Exception:
        tz = timezone(timedelta(hours=2))  # summer offset fallback
    now = datetime.now(tz)
    days_ahead = (config.ARRIVAL_WEEKDAY - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    target = (now + timedelta(days=days_ahead)).replace(
        hour=config.ARRIVAL_HOUR,
        minute=config.ARRIVAL_MINUTE,
        second=0,
        microsecond=0,
    )
    return target.isoformat()


def _request(path, params):
    """GET with retry and backoff. Returns parsed JSON or raises."""
    url = config.API_BASE + path
    session = _get_session()
    last_err = None
    for attempt in range(config.API_MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=config.API_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = f"HTTP {resp.status_code}"
                time.sleep(1.5 * (attempt + 1))
                continue
            resp.raise_for_status()
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"request failed for {path}: {last_err}")


# Geocoding and station lookup
def geocode(query, fallback=None):
    """Resolve an address or place to (lat, lon). Fall back if the API fails."""
    try:
        data = _request("/locations", {"query": query, "results": 1})
        if data:
            item = data[0]
            if "location" in item and item["location"]:
                loc = item["location"]
                return loc["latitude"], loc["longitude"]
            if "latitude" in item:
                return item["latitude"], item["longitude"]
    except Exception:
        pass
    return fallback


def nearby_stops(lat, lon, results=6, distance_m=2500):
    """Return nearby transit stops as a list of dicts."""
    try:
        data = _request(
            "/stops/nearby",
            {"latitude": lat, "longitude": lon, "results": results, "distance": distance_m},
        )
        out = []
        for s in data:
            loc = s.get("location", {})
            out.append(
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "lat": loc.get("latitude"),
                    "lon": loc.get("longitude"),
                    "distance_m": s.get("distance"),
                }
            )
        return out
    except Exception:
        return []


# Journey
def _parse_iso(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _leg_minutes(leg):
    dep = leg.get("departure") or leg.get("plannedDeparture")
    arr = leg.get("arrival") or leg.get("plannedArrival")
    if not dep or not arr:
        return 0.0
    return (_parse_iso(arr) - _parse_iso(dep)).total_seconds() / 60.0


def _parse_journey(journey):
    legs = journey.get("legs", [])
    if not legs:
        return None
    dep = legs[0].get("departure") or legs[0].get("plannedDeparture")
    arr = legs[-1].get("arrival") or legs[-1].get("plannedArrival")
    if not dep or not arr:
        return None
    duration = (_parse_iso(arr) - _parse_iso(dep)).total_seconds() / 60.0
    transit_legs = [l for l in legs if not l.get("walking")]
    n_transfers = max(len(transit_legs) - 1, 0)
    access_walk = _leg_minutes(legs[0]) if legs[0].get("walking") else 0.0
    return {
        "duration_min": round(duration, 1),
        "n_transfers": n_transfers,
        "access_walk_min": round(access_walk, 1),
        "source": "api",
    }


def _estimate(from_lat, from_lon, to_lat, to_lon):
    """Fallback estimate when the API is unavailable.

    Effective door-to-door transit speed is assumed at 24 km/h, with fixed
    access and egress walking of 12 minutes total, plus a distance-based
    transfer allowance.
    """
    dist = haversine_km(from_lat, from_lon, to_lat, to_lon) * config.DETOUR_FACTOR
    in_vehicle = dist / 24.0 * 60.0
    access_walk = 6.0
    egress_walk = 6.0
    n_transfers = min(int(dist // 8), 3)
    transfer_penalty = 4.0 * n_transfers
    duration = in_vehicle + access_walk + egress_walk + transfer_penalty
    return {
        "duration_min": round(duration, 1),
        "n_transfers": n_transfers,
        "access_walk_min": access_walk,
        "source": "estimate",
    }


def get_commute(from_lat, from_lon, to_lat, to_lon, arrival_iso=None, use_api=True):
    # Return a commute result dict. Uses cache, then API, then estimate!
    cache = _load_cache()
    key = f"{round(from_lat,5)},{round(from_lon,5)}->{round(to_lat,5)},{round(to_lon,5)}"
    if key in cache:
        return cache[key]

    result = None
    if use_api:
        if arrival_iso is None:
            arrival_iso = next_arrival_iso()
        params = {
            "from.latitude": from_lat,
            "from.longitude": from_lon,
            "from.address": "home",
            "to.latitude": to_lat,
            "to.longitude": to_lon,
            "to.address": "workplace",
            "arrival": arrival_iso,
            "results": 1,
            "stopovers": "false",
        }
        try:
            data = _request("/journeys", params)
            journeys = data.get("journeys", [])
            if journeys:
                result = _parse_journey(journeys[0])
            time.sleep(config.API_SLEEP)
        except Exception:
            result = None

    if result is None:
        result = _estimate(from_lat, from_lon, to_lat, to_lon)

    cache[key] = result
    return result
