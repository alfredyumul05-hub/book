# Linear MultiCrawler + Scraper

This tool automates the district staff-directory research in linear 50-row batches.

## Install

```bash
python -m pip install httpx beautifulsoup4
```

## Input format

Provide a CSV with columns:

- `District name`
- `City`
- `County name`

## Run

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

## Output

Writes normalized output with the same schema used by prior batches:

- `batch`, `state`, `priority_order`, `district_name`, `city`, `county`
- `staff_directory_url`, `page_title`
- `visibility_status`, `names_visible`, `emails_visible`
- `observed_email_domains`, `email_pattern_or_note`
- `source_method`, `checked_candidates`
