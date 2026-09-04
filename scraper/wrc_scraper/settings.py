import sys
from pathlib import Path

# Let the spider import the shared `common` package that lives at the repo root,
# one level above this Scrapy project.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.config import get_settings  # noqa: E402

_settings = get_settings()

BOT_NAME = "wrc_scraper"

SPIDER_MODULES = ["wrc_scraper.spiders"]
NEWSPIDER_MODULE = "wrc_scraper.spiders"

ROBOTSTXT_OBEY = True
USER_AGENT = _settings.user_agent

CONCURRENT_REQUESTS = _settings.concurrent_requests
CONCURRENT_REQUESTS_PER_DOMAIN = min(_settings.concurrent_requests, 8)
DOWNLOAD_DELAY = _settings.download_delay

AUTOTHROTTLE_ENABLED = _settings.autothrottle_enabled
AUTOTHROTTLE_START_DELAY = _settings.download_delay
AUTOTHROTTLE_TARGET_CONCURRENCY = _settings.autothrottle_target_concurrency

RETRY_ENABLED = True
RETRY_TIMES = _settings.retry_times
RETRY_HTTP_CODES = [429, 500, 502, 503, 504, 522, 524, 408]

ITEM_PIPELINES = {
    "wrc_scraper.pipelines.MongoMinioPipeline": 300,
}

LOG_ENABLED = False  # structured logging is handled by common.logging_config
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"