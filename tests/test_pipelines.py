from unittest.mock import patch

import wrc_scraper.pipelines as pipelines_module
from wrc_scraper.items import CaseItem


class FakeCollection:
    def __init__(self):
        self.docs = {}

    def find_one(self, query):
        return self.docs.get(query["_id"])

    def update_one(self, query, update, upsert=False):
        doc_id = query["_id"]
        doc = self.docs.get(doc_id)
        if doc is None:
            if not upsert:
                return
            doc = {"_id": doc_id}
            self.docs[doc_id] = doc
        for k, v in update.get("$set", {}).items():
            doc[k] = v
        for k, v in update.get("$push", {}).items():
            doc.setdefault(k, []).append(v)

    def replace_one(self, query, doc, upsert=False):
        self.docs[query["_id"]] = doc


def make_item(identifier="ADJ-1", content=b"hello"):
    item = CaseItem()
    item["identifier"] = identifier
    item["description"] = "desc"
    item["body"] = "Workplace Relations Commission"
    item["published_date"] = "2024-01-01"
    item["partition_date"] = "2024-01"
    item["doc_url"] = "https://example/adj-1.html"
    item["raw_content"] = content
    item["content_type"] = "text/html"
    return item


def _make_pipeline(fake_collection):
    with patch("wrc_scraper.pipelines.get_db") as mock_get_db, patch(
        "wrc_scraper.pipelines.ensure_bucket"
    ):
        settings = pipelines_module.get_settings()
        mock_get_db.return_value = {settings.mongo_raw_collection: fake_collection}
        pipeline = pipelines_module.MongoMinioPipeline()
        pipeline.open_spider(spider=None)
    return pipeline


def test_second_identical_scrape_is_skipped_not_reuploaded():
    fake_collection = FakeCollection()
    pipeline = _make_pipeline(fake_collection)

    with patch("wrc_scraper.pipelines.upload_bytes") as mock_upload:
        pipeline.process_item(make_item(content=b"same bytes"), spider=None)
        pipeline.process_item(make_item(content=b"same bytes"), spider=None)

    assert mock_upload.call_count == 1
    assert pipeline.stats == {"found": 2, "scraped": 1, "failed": 0, "skipped": 1}
    assert fake_collection.docs["ADJ-1"]["file_type"] == "html"


def test_changed_content_creates_new_version_without_overwriting():
    fake_collection = FakeCollection()
    pipeline = _make_pipeline(fake_collection)

    with patch("wrc_scraper.pipelines.upload_bytes") as mock_upload:
        pipeline.process_item(make_item(content=b"v1"), spider=None)
        pipeline.process_item(make_item(content=b"v2 different"), spider=None)

    assert mock_upload.call_count == 2
    assert pipeline.stats["scraped"] == 2
    second_call_key = mock_upload.call_args_list[1].args[1]
    assert "_v2" in second_call_key


def test_upsert_by_identifier_keeps_single_record():
    fake_collection = FakeCollection()
    pipeline = _make_pipeline(fake_collection)

    with patch("wrc_scraper.pipelines.upload_bytes"):
        pipeline.process_item(make_item(content=b"v1"), spider=None)
        pipeline.process_item(make_item(content=b"v2 different"), spider=None)

    assert len(fake_collection.docs) == 1