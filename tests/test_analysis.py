import numpy as np
import pandas as pd
import pytest

from climate.analysis import annual_summary, decade_comparison, warming_trends


@pytest.fixture
def daily() -> pd.DataFrame:
    """Two cities, 10 full years. City A warms exactly 0.03 °C/year, city B is flat."""
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    frames = []
    for city, slope in [("A", 0.03), ("B", 0.0)]:
        years = dates.year - 2000
        mean = 15 + slope * years
        frames.append(
            pd.DataFrame(
                {
                    "city": city,
                    "country": "X",
                    "date": dates,
                    "temp_mean": mean,
                    "temp_max": mean + 5,
                    "temp_min": mean - 5,
                    "precipitation": 1.0,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_annual_summary_aggregates_per_city_and_year(daily):
    annual = annual_summary(daily)
    assert len(annual) == 20
    first = annual[(annual["city"] == "A") & (annual["year"] == 2000)].iloc[0]
    assert first["temp_mean"] == pytest.approx(15.0)
    assert first["precipitation"] == pytest.approx(366.0)  # 2000 is a leap year


def test_annual_summary_drops_incomplete_years(daily):
    partial = daily[daily["date"] < "2009-06-01"]
    annual = annual_summary(partial)
    assert 2009 not in annual["year"].tolist()


def test_warming_trend_in_degrees_per_decade(daily):
    trends = warming_trends(annual_summary(daily)).set_index("city")
    assert trends.loc["A", "trend_c_per_decade"] == pytest.approx(0.3)
    assert trends.loc["B", "trend_c_per_decade"] == pytest.approx(0.0, abs=1e-9)
    assert trends.index[0] == "A"  # sorted by warming, descending


def test_decade_comparison(daily):
    result = decade_comparison(annual_summary(daily), first=(2000, 2004), last=(2005, 2009))
    result = result.set_index("city")
    expected = np.mean([0.03 * y for y in range(5, 10)]) - np.mean([0.03 * y for y in range(5)])
    assert result.loc["A", "change_c"] == pytest.approx(expected)
