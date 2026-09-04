from functools import lru_cache

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from common.config import get_settings


@lru_cache
def get_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(settings.mongo_uri)


def get_db(transformed: bool = False) -> Database:
    settings = get_settings()
    db_name = settings.mongo_transformed_db_name if transformed else settings.mongo_db_name
    return get_client()[db_name]


def ensure_indexes() -> None:
    settings = get_settings()

    raw = get_db(transformed=False)[settings.mongo_raw_collection]
    raw.create_index([("partition_date", ASCENDING)])
    raw.create_index([("body", ASCENDING)])

    transformed = get_db(transformed=True)[settings.mongo_transformed_collection]
    transformed.create_index([("partition_date", ASCENDING)])