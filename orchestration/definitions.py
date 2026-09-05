"""Dagster wiring for the WRC pipeline: scrape (per month x body) -> transform.

Run locally with:
    dagster dev -f orchestration/definitions.py
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import dagster as dg  # noqa: E402

from common.config import get_settings  # noqa: E402
from transform.transform import run_transform  # noqa: E402

settings = get_settings()

month_partitions = dg.MonthlyPartitionsDefinition(start_date=settings.orchestration_start_date)
body_partitions = dg.StaticPartitionsDefinition(settings.bodies)
scrape_partitions = dg.MultiPartitionsDefinition(
    {"month": month_partitions, "body": body_partitions}
)


def _month_bounds(month_key: str) -> tuple[date, date]:
    start = date.fromisoformat(month_key)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end


@dg.asset(
    name="scrape_partition_body",
    partitions_def=scrape_partitions,
    retry_policy=dg.RetryPolicy(max_retries=3, delay=10),
)
def scrape_partition_body(context: dg.AssetExecutionContext) -> None:
    keys = context.partition_key.keys_by_dimension
    start, end = _month_bounds(keys["month"])
    body = keys["body"]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "wrc_spider",
            "-a",
            f"start_date={start.isoformat()}",
            "-a",
            f"end_date={end.isoformat()}",
            "-a",
            f"body={body}",
        ],
        cwd=REPO_ROOT / "scraper",
        capture_output=True,
        text=True,
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise RuntimeError(f"scrapy crawl failed with exit code {result.returncode}")


@dg.asset(
    name="transform_range",
    partitions_def=month_partitions,
    deps=[
        dg.AssetDep(
            "scrape_partition_body",
            partition_mapping=dg.MultiToSingleDimensionPartitionMapping(),
        )
    ],
)
def transform_range(context: dg.AssetExecutionContext) -> None:
    start, end = _month_bounds(context.partition_key)
    run_transform(start, end)


defs = dg.Definitions(
    assets=[scrape_partition_body, transform_range],
)