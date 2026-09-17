from functools import lru_cache

from pymongo import ASCENDING, AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase
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


@lru_cache
def get_async_client() -> AsyncMongoClient:
    """PyMongo's native async client (stable since 4.13, replacing Motor,
    which MongoDB deprecated in May 2026). Used by the Scrapy pipeline so
    Mongo I/O doesn't block the asyncio event loop while other requests are
    in flight; the sync client above still covers transform.py and
    scripts/init_infra.py, which have no need for it."""
    settings = get_settings()
    return AsyncMongoClient(settings.mongo_uri)


def get_async_db(transformed: bool = False) -> AsyncDatabase:
    settings = get_settings()
    db_name = settings.mongo_transformed_db_name if transformed else settings.mongo_db_name
    return get_async_client()[db_name]


def ensure_indexes() -> None:
    settings = get_settings()

    raw = get_db(transformed=False)[settings.mongo_raw_collection]
    raw.create_index([("partition_date", ASCENDING)])
    raw.create_index([("body", ASCENDING)])

    transformed = get_db(transformed=True)[settings.mongo_transformed_collection]
    transformed.create_index([("partition_date", ASCENDING)])