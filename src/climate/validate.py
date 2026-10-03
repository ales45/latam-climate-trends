"""Data quality checks. Each check returns a human-readable issue; an empty list means clean."""

import pandas as pd

TEMP_RANGE = (-60.0, 60.0)
TEMP_COLUMNS = ["temp_mean", "temp_max", "temp_min"]


def validate(df: pd.DataFrame) -> list[str]:
    issues: list[str] = []

    nulls = df[TEMP_COLUMNS + ["precipitation"]].isna().sum()
    for column, count in nulls[nulls > 0].items():
        issues.append(f"{column}: {count} null values")

    duplicates = df.duplicated(subset=["city", "date"]).sum()
    if duplicates:
        issues.append(f"{duplicates} duplicate city/date rows")

    for city, group in df.groupby("city"):
        expected = pd.date_range(group["date"].min(), group["date"].max(), freq="D")
        missing = expected.difference(group["date"])
        if len(missing):
            issues.append(f"{city}: {len(missing)} missing dates")

    low, high = TEMP_RANGE
    for column in TEMP_COLUMNS:
        out_of_range = (~df[column].dropna().between(low, high)).sum()
        if out_of_range:
            issues.append(f"{column} out of range: {out_of_range} rows")

    inconsistent = (df["temp_min"] > df["temp_max"]).sum()
    if inconsistent:
        issues.append(f"temp_min > temp_max: {inconsistent} rows")

    negative_rain = (df["precipitation"] < 0).sum()
    if negative_rain:
        issues.append(f"negative precipitation: {negative_rain} rows")

    return issues
