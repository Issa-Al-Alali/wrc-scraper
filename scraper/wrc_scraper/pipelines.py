import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.config import get_settings  # noqa: E402
from common.hashing import sha256_of_bytes  # noqa: E402
from common.logging_config import setup_logging  # noqa: E402
from common.mongo_client import get_db  # noqa: E402
from common.storage_client import ensure_bucket, upload_bytes  # noqa: E402

logger = setup_logging("wrc_scraper.pipeline")

_EXT_BY_CONTENT_TYPE = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def _extension_for(content_type: str) -> str:
    base = (content_type or "").split(";")[0].strip().lower()
    return _EXT_BY_CONTENT_TYPE.get(base, "html")


class MongoMinioPipeline:
    def __init__(self):
        self.settings = get_settings()
        self.stats = {"found": 0, "scraped": 0, "failed": 0, "skipped": 0}

    def open_spider(self, spider):
        ensure_bucket(self.settings.minio_raw_bucket)
        self.collection = get_db(transformed=False)[self.settings.mongo_raw_collection]
        self.started_at = datetime.now(UTC)

    def close_spider(self, spider):
        duration_seconds = (datetime.now(UTC) - self.started_at).total_seconds()
        logger.info(
            "run_summary",
            extra={
                "event": "run_summary",
                "spider": spider.name,
                "duration_seconds": duration_seconds,
                **self.stats,
            },
        )

    def process_item(self, item, spider):
        self.stats["found"] += 1
        raw_content: bytes = item["raw_content"]
        content_type: str = item.get("content_type") or "text/html"
        identifier = item["identifier"]

        try:
            file_hash = f"sha256:{sha256_of_bytes(raw_content)}"
            ext = _extension_for(content_type)
            existing = self.collection.find_one({"_id": identifier})
            now = datetime.now(UTC).isoformat()

            if existing and existing.get("file_hash") == file_hash:
                self.collection.update_one(
                    {"_id": identifier}, {"$set": {"last_seen_at": now}}
                )
                self.stats["skipped"] += 1
                return item

            if existing:
                version = existing.get("_version", 1) + 1
                key = f"raw/{item['body']}/{item['partition_date']}/{identifier}_v{version}.{ext}"
            else:
                version = 1
                key = f"raw/{item['body']}/{item['partition_date']}/{identifier}.{ext}"

            upload_bytes(self.settings.minio_raw_bucket, key, raw_content, content_type)

            doc = {
                "_id": identifier,
                "identifier": identifier,
                "description": item.get("description"),
                "body": item["body"],
                "published_date": item.get("published_date"),
                "partition_date": item["partition_date"],
                "doc_url": item["doc_url"],
                "file_path": key,
                "file_hash": file_hash,
                "file_type": ext,
                "_version": version,
                "last_seen_at": now,
            }
            if existing:
                doc["first_scraped_at"] = existing.get("first_scraped_at", now)
                doc["scrape_errors"] = existing.get("scrape_errors", [])
            else:
                doc["first_scraped_at"] = now
                doc["scrape_errors"] = []

            self.collection.replace_one({"_id": identifier}, doc, upsert=True)
            self.stats["scraped"] += 1

        except Exception as exc:
            self.stats["failed"] += 1
            logger.error(
                "download_failed",
                extra={
                    "event": "download_failed",
                    "identifier": identifier,
                    "url": item.get("doc_url"),
                    "error": str(exc),
                },
            )
            self.collection.update_one(
                {"_id": identifier},
                {"$push": {"scrape_errors": str(exc)}},
                upsert=True,
            )

        return item