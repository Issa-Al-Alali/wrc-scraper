# WRC Legal Document Scraping Pipeline

Scrapes case decisions from the Irish Workplace Relations Commission
(workplacerelations.ie), stores metadata in MongoDB and documents in MinIO,
and transforms raw HTML into cleaned content — all orchestrated with Dagster.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design rationale.

## Prerequisites

- Docker Desktop
- Python 3.13

## Setup

```bash
cp .env.example .env

python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

docker compose up -d
python scripts/init_infra.py    # creates MinIO buckets + Mongo indexes
```

## Running the scraper standalone

```bash
cd scraper
scrapy crawl wrc_spider -a start_date=2024-01-01 -a end_date=2024-02-01 -a body="Workplace Relations Commission"
```

`body` must be one of the values in `WRC_BODIES` (see `.env`).

## Running the transform step standalone

```bash
python transform/transform.py --start 2024-01-01 --end 2024-02-01
```

## Running the full pipeline via Dagster

```bash
dagster dev -f orchestration/definitions.py
```

Open the Dagster UI (default http://localhost:3000), materialize
`scrape_partition_body` partitions for the month/body combinations you want,
then materialize the corresponding `transform_range` partition. Or launch the
`wrc_pipeline` job directly for a full backfill.

## Tests

```bash
pytest
```

## Environment variables

All configurable values live in `.env` (see `.env.example` for the full list
and defaults): Mongo connection/collection names, MinIO endpoint/buckets,
scraper throttling knobs, the list of bodies to scrape, and logging settings.