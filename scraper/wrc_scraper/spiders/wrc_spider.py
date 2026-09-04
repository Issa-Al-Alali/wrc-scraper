import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import scrapy  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from common.config import get_settings  # noqa: E402
from common.date_extraction import extract_published_date  # noqa: E402
from common.logging_config import setup_logging  # noqa: E402
from common.partitioning import generate_partitions  # noqa: E402
from common.wrc_bodies import body_for_identifier, body_from_content  # noqa: E402
from wrc_scraper.items import CaseItem  # noqa: E402

logger = setup_logging("wrc_scraper.spider")

MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

PAGE_NUMBER_RE = re.compile(r"pageNumber=(\d+)")


class WrcSpider(scrapy.Spider):
    """Scrapes WRC/Labour Court/Equality Tribunal/EAT case decisions for one
    (date range, body) pair. The site organizes decisions by calendar month
    at `/en/cases/{year}/{month}/` regardless of the requested date range, so
    this spider always walks month by month within [start_date, end_date)
    and filters records down to the requested body — see ARCHITECTURE.md.
    """

    name = "wrc_spider"

    def __init__(self, start_date=None, end_date=None, body=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not (start_date and end_date and body):
            raise ValueError("start_date, end_date and body are all required spider arguments")

        self.start_date = date.fromisoformat(start_date)
        self.end_date = date.fromisoformat(end_date)
        self.body = body
        self.base_url = get_settings().wrc_base_url

        self.found = 0
        self.matched = 0
        self.partition_stats: dict[str, dict[str, int]] = {}

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        for month_start, _, label in generate_partitions(self.start_date, self.end_date, "monthly"):
            self.partition_stats[label] = {"found": 0, "matched": 0}
            logger.info(
                "partition_start",
                extra={
                    "event": "partition_start",
                    "body": self.body,
                    "partition": label,
                    "start_date": str(self.start_date),
                    "end_date": str(self.end_date),
                },
            )
            url = f"{self.base_url}{month_start.year}/{MONTH_NAMES[month_start.month - 1]}/"
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                errback=self.handle_listing_error,
                meta={"partition_date": label, "page": 1, "url_base": url},
            )

    def parse_listing(self, response):
        partition_date = response.meta["partition_date"]

        for el in response.css(".each-item"):
            href = el.css("h2.title a::attr(href)").get()
            if not href:
                continue
            identifier = href.rsplit("/", 1)[-1].removesuffix(".html").upper()
            description = " ".join((el.css("p.desc::text").get() or "").split())

            self.found += 1
            self.partition_stats[partition_date]["found"] += 1

            record_body = body_for_identifier(identifier)
            if record_body != self.body:
                continue

            self.matched += 1
            self.partition_stats[partition_date]["matched"] += 1

            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_detail,
                errback=self.handle_detail_error,
                meta={
                    "identifier": identifier,
                    "description": description,
                    "partition_date": partition_date,
                    "prefix_body": record_body,
                },
            )

        page_numbers = [
            int(m.group(1))
            for href in response.css(".pagination a::attr(href)").getall()
            if (m := PAGE_NUMBER_RE.search(href))
        ]
        current_page = response.meta["page"]
        if page_numbers and current_page < max(page_numbers):
            next_page = current_page + 1
            yield scrapy.Request(
                f"{response.meta['url_base']}?pageNumber={next_page}",
                callback=self.parse_listing,
                errback=self.handle_listing_error,
                meta={**response.meta, "page": next_page},
            )

    def handle_listing_error(self, failure):
        response = getattr(failure.value, "response", None)
        if response is not None and response.status == 404:
            # Some early months in the archive were never generated and 404
            # instead of returning an empty listing — treat as "no records".
            logger.info(
                "partition_not_found",
                extra={"event": "partition_not_found", "url": failure.request.url},
            )
            return
        logger.error(
            "partition_error",
            extra={"event": "partition_error", "url": failure.request.url, "error": str(failure.value)},
        )

    def parse_detail(self, response):
        meta = response.meta
        content_type = response.headers.get("Content-Type", b"").decode(errors="ignore")
        soup = BeautifulSoup(response.body, "lxml")
        content_div = soup.select_one("div.content")
        text = content_div.get_text(" ", strip=True) if content_div else ""

        if not text:
            pdf_link = soup.select_one('a[href$=".pdf"]')
            if pdf_link and pdf_link.get("href"):
                yield scrapy.Request(
                    response.urljoin(pdf_link["href"]),
                    callback=self.parse_pdf_fallback,
                    errback=self.handle_detail_error,
                    meta=meta,
                )
                return

            logger.warning(
                "empty_content_no_pdf_fallback",
                extra={
                    "event": "empty_content_no_pdf_fallback",
                    "identifier": meta["identifier"],
                    "url": response.url,
                },
            )
            return

        confirmed_body = body_from_content(text)
        if confirmed_body and confirmed_body != meta["prefix_body"]:
            logger.warning(
                "body_mismatch",
                extra={
                    "event": "body_mismatch",
                    "identifier": meta["identifier"],
                    "prefix_body": meta["prefix_body"],
                    "confirmed_body": confirmed_body,
                },
            )

        yield self._build_item(response, meta, text=text, content_type=content_type or "text/html")

    def parse_pdf_fallback(self, response):
        meta = response.meta
        content_type = response.headers.get("Content-Type", b"application/pdf").decode(errors="ignore")
        yield self._build_item(response, meta, text="", content_type=content_type)

    def _build_item(self, response, meta, *, text: str, content_type: str) -> CaseItem:
        item = CaseItem()
        item["identifier"] = meta["identifier"]
        item["description"] = meta["description"]
        item["body"] = meta["prefix_body"]
        item["published_date"] = extract_published_date(text) if text else None
        item["partition_date"] = meta["partition_date"]
        item["doc_url"] = response.url
        item["scraped_at"] = datetime.now(UTC).isoformat()
        item["raw_content"] = response.body
        item["content_type"] = content_type
        return item

    def handle_detail_error(self, failure):
        logger.error(
            "download_failed",
            extra={
                "event": "download_failed",
                "identifier": failure.request.meta.get("identifier"),
                "url": failure.request.url,
                "status_code": getattr(getattr(failure.value, "response", None), "status", None),
                "error": str(failure.value),
            },
        )

    def closed(self, reason):
        logger.info(
            "spider_closed",
            extra={
                "event": "spider_closed",
                "body": self.body,
                "reason": reason,
                "found": self.found,
                "matched": self.matched,
                "partitions": self.partition_stats,
            },
        )