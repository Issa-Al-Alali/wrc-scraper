import scrapy


class CaseItem(scrapy.Item):
    identifier = scrapy.Field()
    description = scrapy.Field()
    body = scrapy.Field()
    published_date = scrapy.Field()
    partition_date = scrapy.Field()
    doc_url = scrapy.Field()
    scraped_at = scrapy.Field()

    # Transient fields consumed by the pipeline, never persisted to Mongo.
    raw_content = scrapy.Field()
    content_type = scrapy.Field()