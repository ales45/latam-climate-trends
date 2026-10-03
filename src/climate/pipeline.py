"""Entry point: extract -> validate -> analyze -> report."""

import logging
from pathlib import Path

from climate.analysis import annual_summary, decade_comparison, warming_trends
from climate.cities import CITIES
from climate.extract import extract
from climate.report import plot_annual_temperatures, plot_warming_rates, write_summary
from climate.validate import validate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
START, END = "1995-01-01", "2024-12-31"

logger = logging.getLogger("climate")


class DataQualityError(Exception):
    pass


def run() -> None:
    daily = extract(CITIES, START, END, cache_dir=RAW_DIR)
    logger.info("Extracted %d rows", len(daily))

    issues = validate(daily)
    for issue in issues:
        logger.warning("Data quality: %s", issue)
    if any("null" in issue or "missing dates" in issue for issue in issues):
        raise DataQualityError("Blocking data quality issues found, see warnings above")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    daily.to_csv(PROCESSED_DIR / "daily_weather.csv", index=False)

    annual = annual_summary(daily)
    annual.to_csv(PROCESSED_DIR / "annual_summary.csv", index=False)
    trends = warming_trends(annual)
    decades = decade_comparison(annual, first=(1995, 2004), last=(2015, 2024))

    figures_dir = REPORTS_DIR / "figures"
    plot_annual_temperatures(annual, trends, figures_dir)
    plot_warming_rates(trends, figures_dir)
    write_summary(trends, decades, issues, len(daily), REPORTS_DIR)
    logger.info("Pipeline finished")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
