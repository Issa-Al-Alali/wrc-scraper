from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Mongo
    mongo_root_user: str = "admin"
    mongo_root_password: str = "changeme"
    mongo_uri: str = "mongodb://admin:changeme@localhost:27017"
    mongo_db_name: str = "wrc_landing"
    mongo_transformed_db_name: str = "wrc_transformed"
    mongo_raw_collection: str = "cases_raw"
    mongo_transformed_collection: str = "cases_transformed"

    # MinIO / S3
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme123"
    minio_endpoint_url: str = "http://localhost:9000"
    minio_raw_bucket: str = "wrc-landing-docs"
    minio_transformed_bucket: str = "wrc-transformed-docs"

    # Scraper behavior
    wrc_base_url: str = "https://www.workplacerelations.ie/en/cases/"
    partition_size: str = "monthly"
    concurrent_requests: int = 8
    download_delay: float = 0.5
    autothrottle_enabled: bool = True
    autothrottle_target_concurrency: float = 4
    retry_times: int = 3
    user_agent: str = "wrc-research-scraper (+contact-email@example.com)"

    wrc_bodies: str = (
        "Employment Appeals Tribunal,Equality Tribunal,Labour Court,"
        "Workplace Relations Commission"
    )

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"

    @property
    def bodies(self) -> list[str]:
        return [b.strip() for b in self.wrc_bodies.split(",") if b.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()