"""Analysis: annual aggregates, linear warming trends and decade-over-decade change."""

import numpy as np
import pandas as pd


def annual_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to one row per city and year, keeping only complete years."""
    df = daily.assign(year=daily["date"].dt.year)
    annual = df.groupby(["city", "country", "year"], as_index=False).agg(
        temp_mean=("temp_mean", "mean"),
        temp_max=("temp_max", "mean"),
        temp_min=("temp_min", "mean"),
        precipitation=("precipitation", "sum"),
        days=("date", "nunique"),
    )
    days_in_year = np.where(pd.Series(annual["year"]).map(_is_leap), 366, 365)
    complete = annual["days"] == days_in_year
    return annual[complete].drop(columns="days").reset_index(drop=True)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def warming_trends(annual: pd.DataFrame) -> pd.DataFrame:
    """Least-squares slope of annual mean temperature, expressed in °C per decade."""
    rows = []
    for (city, country), group in annual.groupby(["city", "country"]):
        slope, _ = np.polyfit(group["year"], group["temp_mean"], deg=1)
        rows.append({"city": city, "country": country, "trend_c_per_decade": slope * 10})
    return (
        pd.DataFrame(rows).sort_values("trend_c_per_decade", ascending=False).reset_index(drop=True)
    )


def decade_comparison(
    annual: pd.DataFrame, first: tuple[int, int], last: tuple[int, int]
) -> pd.DataFrame:
    """Difference in average annual temperature and rainfall between two periods."""

    def period_mean(bounds: tuple[int, int]) -> pd.DataFrame:
        in_period = annual["year"].between(*bounds)
        return annual[in_period].groupby("city")[["temp_mean", "precipitation"]].mean()

    before, after = period_mean(first), period_mean(last)
    result = pd.DataFrame(
        {
            "temp_before": before["temp_mean"],
            "temp_after": after["temp_mean"],
            "change_c": after["temp_mean"] - before["temp_mean"],
            "rain_change_pct": (after["precipitation"] / before["precipitation"] - 1),
        }
    )
    return result.reset_index().sort_values("change_c", ascending=False)
