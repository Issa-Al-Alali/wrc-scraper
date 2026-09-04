"""Create MinIO buckets and Mongo indexes if they don't already exist.

Run once after `docker compose up`:
    python scripts/init_infra.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.config import get_settings  # noqa: E402
from common.mongo_client import ensure_indexes  # noqa: E402
from common.storage_client import ensure_bucket  # noqa: E402


def main() -> None:
    settings = get_settings()

    ensure_bucket(settings.minio_raw_bucket)
    ensure_bucket(settings.minio_transformed_bucket)
    print(f"Ensured buckets: {settings.minio_raw_bucket}, {settings.minio_transformed_bucket}")

    ensure_indexes()
    print("Ensured Mongo indexes")


if __name__ == "__main__":
    main()