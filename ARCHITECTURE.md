# Architecture

## Partition size: monthly

The site itself organizes decisions by calendar month at
`/en/cases/{year}/{month}/`, paginated ~100 records per page — a busy month
(e.g. July 2025) runs to 3 pages, a few hundred records, well under any
pagination/rate-limit pain. Monthly is also the smallest granularity that
maps 1:1 onto a real URL on the site; weekly would multiply HTTP requests for
no gain (the site doesn't organize by week), and quarterly would make each
partition's retry/backfill unit too coarse. `generate_partitions` in
`common/partitioning.py` also supports weekly/quarterly for completeness and
configurability, but monthly (`PARTITION_SIZE=monthly`) is the only one that
lines up with how the spider actually builds URLs.

## The real site has no server-side search — it's a browsable URL structure

The spec assumed `/en/cases/` exposed a filterable search form. In practice
that page's result list (`<div class="item-list">`) is populated by
client-side JS with no discoverable API — but the site also serves fully
server-rendered listing pages at `/en/cases/{year}/{month}/`, paginated via
`?pageNumber=N`, going back to at least 1986. This is simpler than a search
API: no JS rendering, no headless browser, just a GET request. This is why
`ROBOTSTXT_OBEY = True` is safe — robots.txt disallows `/en/Cases/` and
`/en/EAT_Import/` etc. (capital-letter legacy paths) but not the lowercase
`/en/cases/` path this scraper uses.

## Body classification: prefix-based, not a server-side filter

There's no way to ask the listing page for only one tribunal's cases — every
month's page mixes all four bodies together, and the only per-record
signal is the identifier prefix (`ADJ-...`, `LCR...`, etc.). Workplace
Relations Commission (`ADJ`, `IR-SC`, `IR`), Equality Tribunal (`DEC-E`,
`DEC-S`) and Employment Appeals Tribunal (`UD`, `MN`, `RP`, `WT`, `PW`, `TE`,
`TU`, `I`, `P`) each use a small, closed set of prefixes — EAT in particular
stopped issuing decisions in 2015, so its set cannot grow. Labour Court's
prefixes are open-ended: legacy `LCR`/`AD`/`EDA`/`DIC` plus newer
subject-specific appeal codes (`DWT`, `FTD`, `HSD`, `PTD`, `UDD`, ...), all
sharing the same "Signed on behalf of the Labour Court" signature block. So
`common/wrc_bodies.py` treats Labour Court as the default classification for
any identifier that isn't in one of the other three closed sets, rather than
maintaining an exhaustive whitelist that would silently miss new codes.

As a cheap correctness check, `parse_detail` also looks for a body-specific
phrase in the fetched page ("ADJUDICATION OFFICER DECISION",
"EQUALITY TRIBUNAL", "EMPLOYMENT APPEALS TRIBUNAL", "Signed on behalf of the
Labour Court") and logs a `body_mismatch` warning if it disagrees with the
prefix-derived classification. It doesn't change what gets stored — it's a
signal for someone to go look, since the identifier is still the most
consistent field to key off.

Trade-off: because classification happens per-record from the identifier
before fetching, and the spider is invoked once per body by the orchestrator,
each body's crawl only ever fetches its own matching detail pages — no
redundant fetching of other bodies' pages within a single body's run.

## Published date: no single consistent field

Confirmed by direct inspection of real pages across all four bodies:

| Body | Where the date lives |
|---|---|
| WRC (ADJ, IR-SC) | Labeled `Dated:   26/08/2025` (`DD/MM/YYYY`) |
| Equality Tribunal (DEC-E) | Labeled `Date of issue:    26th January 2010` |
| Equality Tribunal (DEC-S) | No label — only appears as free text at the very end, after the Equality Officer's name |
| Labour Court | No label — a date in a signature-block table cell after "Signed on behalf of the Labour Court" |
| EAT | No label, inconsistent placement in free text (when text exists at all) |

`common/date_extraction.py` tries, in order: the two labeled patterns, then
text near the Labour Court sign-off phrase, then falls back to the *last*
date-like substring anywhere in the page text (the decision date is
overwhelmingly the last date mentioned, since everything earlier is case
history). If nothing matches, `published_date` is left `None` rather than
guessing — a missing date is better than a wrong one, and it's logged.

## Some EAT-era records are PDF-only, not HTML

A meaningful fraction of EAT records (`UD`, `MN`, `RP`, `WT`, `PW`, `TE`, `I`,
`TU`, `P` prefixes) render with an empty `<div class="content"></div>` — the
actual decision only exists as a scanned PDF linked from that otherwise-empty
page (under `/en/eat_import/...`). This isn't predictable from the prefix or
year alone. The spider checks whether the extracted content text is empty
and, if so, looks for a `.pdf` link on the page and fetches that instead,
storing it with `content_type=application/pdf` and no `published_date`
(EAT free-text date extraction isn't attempted from a page with no text). If
neither inline content nor a PDF link is found, the record is logged
(`empty_content_no_pdf_fallback`) and skipped rather than storing an empty
file.

## A dynamic per-request marker breaks hashing unless stripped

Every page on the site ends with a server-timing HTML comment
(`<!-- Elapsed time: 0.0156007 -->`) that has a different value on every
single fetch, confirmed by requesting the same URL twice in a row and
diffing the bytes. Hashing the raw response as-is would make idempotency
never trigger — every run would look like changed content, and the pipeline
would re-upload a new version of every record on every re-scrape. The spider
strips this one specific comment (`_strip_volatile_markers` in
`wrc_spider.py`) before it becomes `raw_content`, so both the stored bytes
and the hash are stable across runs. No other volatile markers (no
`__VIEWSTATE`, no CSRF token, no session id) were found on these pages.

## Idempotency

`identifier` is the Mongo `_id` — one upsert per case, no separate dedup
collection. On each run: compute the new content hash, compare to the stored
`file_hash`. Identical → skip re-upload, bump `last_seen_at` only. Different
→ upload under a new versioned key (`{identifier}_v2.{ext}`, tracked via an
internal `_version` field) rather than overwriting, and update the record's
`file_path`/`file_hash` to point at the new version. This satisfies "never
mutate Landing Zone data" (the old version's object is never deleted or
overwritten in MinIO) while keeping the metadata record current. Re-running
the same date range is a no-op in the common case: no duplicate Mongo
records, no redundant MinIO uploads.

## Rate limiting

`AUTOTHROTTLE_ENABLED` with a target concurrency of 4, `RETRY_TIMES=3`
covering 429/500/502/503/504, an honest identifying `USER_AGENT`. No
`Crawl-delay` in robots.txt, and manual testing (a dozen sequential requests
at ~1.5s spacing with an honest UA) triggered no rate limiting or WAF
challenge — the site has no aggressive anti-bot posture, so no proxy
rotation or headless browser is used.

## What would change to support 50+ sources

- A per-source plugin architecture: one Scrapy spider + one body-classifier
  module per source, all conforming to a shared interface (`start_requests`
  from a date range, yield a `CaseItem`-shaped item).
- A shared scraping SDK/base spider class factoring out what's currently
  WRC-specific in `wrc_spider.py` (pagination-following, retry/errback
  wiring) so a new source only implements its own listing/detail parsing.
- Replace `subprocess.run(["scrapy", "crawl", ...])` fan-out with a real job
  queue (e.g. Celery or Dagster's own run queue against a remote executor)
  so 50 sources' partitions don't serialize behind one Dagster daemon's
  subprocess pool.
- Move MinIO to real S3 (the boto3 client already only needs an endpoint/
  credential swap) once storage volume and durability requirements outgrow
  a single self-hosted box.
- Shard Mongo (or move to a managed cluster) once collection size and write
  throughput from 50 concurrent sources exceed a single replica set.
- A centralized schema registry per source, since different tribunals/
  jurisdictions won't share WRC's exact metadata shape (this pipeline
  already isolates that variation behind `CaseItem`, but 50 sources would
  need each source's quirks documented and validated in one place rather
  than tribal knowledge in each spider).