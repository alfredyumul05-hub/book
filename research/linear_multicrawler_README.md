# Linear MultiCrawler + Scraper

This tool automates district staff-directory research in linear batches and can push all extracted rows directly to PostgreSQL (including Neon).

## Install

```bash
python -m pip install httpx beautifulsoup4 psycopg[binary]
```

## Input format

Provide a CSV with columns:

- `District name`
- `City`
- `County name`

## Run locally (CSV only)

```bash
python research/linear_multicrawler.py \
  --input-csv research/districts_ca.csv \
  --output-csv research/staff_directory_urls_ca_batch_03.csv \
  --start 101 \
  --end 150 \
  --batch CA-03 \
  --state CA \
  --concurrency 12
```

## Run locally + push to Neon PostgreSQL

```bash
python research/linear_multicrawler.py \
  --input-csv research/districts_ca.csv \
  --output-csv research/staff_directory_urls_ca_batch_03.csv \
  --start 101 \
  --end 150 \
  --batch CA-03 \
  --state CA \
  --concurrency 12 \
  --postgres-url 'postgresql://neondb_owner:npg_mUQ1pY7eCiod@ep-shy-flower-aefcknf0-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require' \
  --postgres-table staff_directory_results
```

## Database behavior

- Auto-creates table (default: `staff_directory_results`) if missing.
- Upserts by primary key: `(batch, state, priority_order)`.
- Re-running the same batch updates existing rows.

## Output schema

- `batch`, `state`, `priority_order`, `district_name`, `city`, `county`
- `staff_directory_url`, `page_title`
- `visibility_status`, `names_visible`, `emails_visible`
- `observed_email_domains`, `email_pattern_or_note`
- `source_method`, `checked_candidates`
