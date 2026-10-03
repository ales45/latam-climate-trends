"""Extract step: download daily weather history from the Open-Meteo archive API."""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from climate.cities import City

logger = logging.getLogger(__name__)

API_URL = "https://archive-api.open-meteo.com/v1/archive"
# Pin a single reanalysis model. The default "best_match" switches models over time,
# which creates artificial jumps (e.g. a -1.8 °C step in Bogota in 2017).
REANALYSIS_MODEL = "era5"
DAILY_VARIABLES = {
    "temperature_2m_mean": "temp_mean",
    "temperature_2m_max": "temp_max",
    "temperature_2m_min": "temp_min",
    "precipitation_sum": "precipitation",
}

Fetcher = Callable[[str], dict]


def build_url(city: City, start: str, end: str) -> str:
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start,
        "end_date": end,
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto",
        "models": REANALYSIS_MODEL,
    }
    return f"{API_URL}?{urllib.parse.urlencode(params, safe=',')}"


def http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def fetch_city(
    city: City,
    start: str,
    end: str,
    fetcher: Fetcher = http_get_json,
    retries: int = 4,
    backoff_seconds: float = 2.0,
    rate_limit_wait_seconds: float = 65.0,
) -> dict:
    """Fetch one city's history, retrying transient failures with exponential backoff."""
    url = build_url(city, start, end)
    for attempt in range(1, retries + 1):
        try:
            return fetcher(url)
        except (ConnectionError, TimeoutError, OSError) as error:
            if attempt == retries:
                raise
            wait = backoff_seconds * 2 ** (attempt - 1)
            if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                wait = max(wait, rate_limit_wait_seconds)  # minutely quota: wait it out
            logger.warning(
                "%s: attempt %d failed (%s), retrying in %.0fs", city.name, attempt, error, wait
            )
            time.sleep(wait)
    raise AssertionError("unreachable")


def parse_daily(payload: dict, city: City) -> pd.DataFrame:
    daily = payload["daily"]
    df = pd.DataFrame({new: daily[old] for old, new in DAILY_VARIABLES.items()})
    df.insert(0, "date", pd.to_datetime(daily["time"]))
    df.insert(0, "country", city.country)
    df.insert(0, "city", city.name)
    return df


def extract(cities: list[City], start: str, end: str, cache_dir: Path) -> pd.DataFrame:
    """Download every city (caching raw JSON so re-runs don't hit the API) and stack them."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for city in cities:
        cache_file = cache_dir / f"{city.name.lower().replace(' ', '_')}_{start}_{end}.json"
        if cache_file.exists():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            logger.info("Downloading %s", city.name)
            payload = fetch_city(city, start, end)
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
            time.sleep(15)  # stay under the free API's per-minute quota
        frames.append(parse_daily(payload, city))
    return pd.concat(frames, ignore_index=True)
