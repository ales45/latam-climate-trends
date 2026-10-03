import pytest

from climate.cities import City
from climate.extract import build_url, fetch_city, parse_daily

PAYLOAD = {
    "daily": {
        "time": ["2024-01-01", "2024-01-02"],
        "temperature_2m_mean": [19.9, 20.9],
        "temperature_2m_max": [29.9, 30.6],
        "temperature_2m_min": [12.3, 12.9],
        "precipitation_sum": [0.0, 1.2],
    }
}
CITY = City("Santiago", "Chile", -33.45, -70.67)


def test_build_url_contains_coordinates_and_variables():
    url = build_url(CITY, "2024-01-01", "2024-01-02")
    assert "latitude=-33.45" in url
    assert "longitude=-70.67" in url
    assert "temperature_2m_mean" in url
    assert "start_date=2024-01-01" in url
    assert "models=era5" in url  # one consistent model avoids artificial trend breaks


def test_parse_daily_returns_tidy_frame():
    df = parse_daily(PAYLOAD, CITY)
    assert list(df.columns) == [
        "city",
        "country",
        "date",
        "temp_mean",
        "temp_max",
        "temp_min",
        "precipitation",
    ]
    assert len(df) == 2
    assert df["city"].unique().tolist() == ["Santiago"]
    assert str(df["date"].dtype).startswith("datetime64")


def test_fetch_retries_on_transient_errors():
    calls = []

    def flaky(url):
        calls.append(url)
        if len(calls) < 3:
            raise ConnectionError("temporary failure")
        return PAYLOAD

    result = fetch_city(CITY, "2024-01-01", "2024-01-02", fetcher=flaky, backoff_seconds=0)
    assert result == PAYLOAD
    assert len(calls) == 3


def test_fetch_gives_up_after_max_retries():
    def broken(url):
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        fetch_city(CITY, "2024-01-01", "2024-01-02", fetcher=broken, backoff_seconds=0, retries=2)


def test_waits_longer_when_rate_limited(monkeypatch):
    import urllib.error

    waits = []
    monkeypatch.setattr("climate.extract.time.sleep", waits.append)
    calls = []

    def limited(url):
        calls.append(url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        return PAYLOAD

    fetch_city(CITY, "2024-01-01", "2024-01-02", fetcher=limited, rate_limit_wait_seconds=65)
    assert waits == [65]
