import pandas as pd

from climate.validate import validate


def make_frame(**overrides) -> pd.DataFrame:
    data = {
        "city": ["Lima"] * 3,
        "country": ["Peru"] * 3,
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        "temp_mean": [20.0, 21.0, 22.0],
        "temp_max": [25.0, 26.0, 27.0],
        "temp_min": [15.0, 16.0, 17.0],
        "precipitation": [0.0, 0.5, 0.0],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_clean_data_has_no_issues():
    assert validate(make_frame()) == []


def test_detects_missing_dates():
    df = make_frame().drop(index=1)
    issues = validate(df)
    assert any("missing dates" in issue for issue in issues)


def test_detects_nulls():
    issues = validate(make_frame(temp_mean=[20.0, None, 22.0]))
    assert any("null" in issue for issue in issues)


def test_detects_inconsistent_min_max():
    issues = validate(make_frame(temp_min=[15.0, 30.0, 17.0]))
    assert any("temp_min > temp_max" in issue for issue in issues)


def test_detects_out_of_range_values():
    issues = validate(make_frame(temp_max=[25.0, 99.0, 27.0], precipitation=[0.0, -1.0, 0.0]))
    assert any("temp_max out of range" in issue for issue in issues)
    assert any("negative precipitation" in issue for issue in issues)


def test_detects_duplicate_days():
    df = pd.concat([make_frame(), make_frame().iloc[[0]]])
    assert any("duplicate" in issue for issue in validate(df))
