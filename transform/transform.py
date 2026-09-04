"""Cleans raw scraped WRC case documents and writes them to the transformed
zone (Mongo `cases_transformed` + MinIO `wrc-transformed-docs`).

Runnable standalone:
    python transform/transform.py --start 2024-01-01 --end 2024-02-01

Also callable as a Dagster asset via `run_transform`.
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup  # noqa: E402

from common.config import get_settings  # noqa: E402
from common.hashing import sha256_of_bytes  # noqa: E402
from common.logging_config import setup_logging  # noqa: E402
from common.mongo_client import get_db  # noqa: E402
from common.storage_client import download_bytes, ensure_bucket, upload_bytes  # noqa: E402

logger = setup_logging("wrc_transform")

PASS_THROUGH_EXTENSIONS = {"pdf", "doc", "docx"}


@dataclass
class TransformSummary:
    processed: int = 0
    skipped: int = 0
    failed: int = 0


def clean_html(raw_html: bytes, identifier: str) -> bytes:
    soup = BeautifulSoup(raw_html, "lxml")
    content = soup.select_one("div.content")
    body_html = content.decode() if content else ""
    cleaned = (
        "<!DOCTYPE html>"
        f'<html lang="en"><head><meta charset="utf-8"><title>{identifier}</title></head>'
        f"<body><h1>{identifier}</h1>{body_html}</body></html>"
    )
    return cleaned.encode("utf-8")


def run_transform(start_date: date, end_date: date) -> TransformSummary:
    settings = get_settings()
    ensure_bucket(settings.minio_transformed_bucket)

    raw_collection = get_db(transformed=False)[settings.mongo_raw_collection]
    transformed_collection = get_db(transformed=True)[settings.mongo_transformed_collection]

    query = {
        "partition_date": {
            "$gte": start_date.strftime("%Y-%m"),
            "$lt": end_date.strftime("%Y-%m"),
        }
    }
    summary = TransformSummary()

    logger.info(
        "transform_start",
        extra={"event": "transform_start", "start_date": str(start_date), "end_date": str(end_date)},
    )

    for record in raw_collection.find(query):
        identifier = record["identifier"]
        try:
            raw_bytes = download_bytes(settings.minio_raw_bucket, record["file_path"])
            ext = record.get("file_type", "html")

            if ext in PASS_THROUGH_EXTENSIONS:
                out_bytes = raw_bytes
            else:
                out_bytes = clean_html(raw_bytes, identifier)

            transformed_hash = f"sha256:{sha256_of_bytes(out_bytes)}"
            transformed_key = f"{identifier}.{ext}"

            existing = transformed_collection.find_one({"_id": identifier})
            if existing and existing.get("transformed_file_hash") == transformed_hash:
                summary.skipped += 1
                continue

            upload_bytes(settings.minio_transformed_bucket, transformed_key, out_bytes)

            doc = dict(record)
            doc["_id"] = identifier
            doc["transformed_file_path"] = transformed_key
            doc["transformed_file_hash"] = transformed_hash
            doc["transformed_at"] = datetime.now(UTC).isoformat()

            transformed_collection.replace_one({"_id": identifier}, doc, upsert=True)
            summary.processed += 1

        except Exception as exc:
            summary.failed += 1
            logger.error(
                "transform_failed",
                extra={"event": "transform_failed", "identifier": identifier, "error": str(exc)},
            )

    logger.info(
        "transform_summary",
        extra={
            "event": "transform_summary",
            "processed": summary.processed,
            "skipped": summary.skipped,
            "failed": summary.failed,
        },
    )
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform raw WRC case documents")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_transform(args.start, args.end)