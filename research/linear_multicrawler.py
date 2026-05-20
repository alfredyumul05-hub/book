#!/usr/bin/env python3
"""Linear multi-crawler for school district staff directory discovery.

Given an input CSV with district rows, this script concurrently probes candidate
staff-directory URLs, writes normalized CSV output, and can upsert results into
PostgreSQL (e.g., Neon).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import psycopg
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NAME_HINT_RE = re.compile(r"\b(staff|directory|teacher|principal|counselor|superintendent)\b", re.I)

COMMON_PATHS = [
    "/apps/staff/",
    "/staff",
    "/staff-directory",
    "/directory",
    "/about/staff",
    "/contact-us",
]


@dataclass
class DistrictRow:
    priority_order: int
    district_name: str
    city: str
    county: str
    state: str


@dataclass
class CrawlResult:
    batch: str
    state: str
    priority_order: int
    district_name: str
    city: str
    county: str
    staff_directory_url: str
    page_title: str
    visibility_status: str
    names_visible: str
    emails_visible: str
    observed_email_domains: str
    email_pattern_or_note: str
    source_method: str
    checked_candidates: str


async def fetch_text(client: httpx.AsyncClient, url: str) -> tuple[int, str]:
    try:
        r = await client.get(url, follow_redirects=True)
        return r.status_code, r.text[:300000]
    except Exception:
        return 0, ""


def detect_visibility(html: str) -> tuple[str, str, str, str, str, str]:
    if not html:
        return ("not_verified_visible", "unknown", "unknown", "", "no page text fetched", "")

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    title = soup.title.text.strip() if soup.title and soup.title.text else ""

    emails = sorted(set(EMAIL_RE.findall(text)))
    domains = sorted({e.split("@", 1)[1].lower() for e in emails})

    has_names = bool(NAME_HINT_RE.search(text))
    has_emails = bool(emails)

    if has_names and has_emails:
        status = "visible_names_and_emails"
        note = "published names and emails detected"
    elif has_names:
        status = "visible_names_no_emails"
        note = "staff-related terms detected, no visible emails"
    elif has_emails:
        status = "partial_contacts_only"
        note = "emails detected without clear staff directory markers"
    else:
        status = "not_verified_visible"
        note = "no strong staff markers detected"

    return (
        status,
        "yes" if has_names else "no",
        "yes" if has_emails else "no",
        "; ".join(domains),
        f"{note}; emails_found={len(emails)}",
        title,
    )


def build_candidates(district_name: str) -> list[str]:
    slug = district_name.lower().replace(" district", "").replace(" ", "-")
    base_candidates = [
        f"https://www.{slug}.org",
        f"https://www.{slug}.k12.ca.us",
        f"https://{slug}.org",
    ]
    candidates: list[str] = []
    for base in base_candidates:
        candidates.extend(urljoin(base, path) for path in COMMON_PATHS)
    return candidates


async def crawl_one(client: httpx.AsyncClient, row: DistrictRow, batch: str) -> CrawlResult:
    candidates = build_candidates(row.district_name)

    best: tuple[str, str, str, str, str, str, str] | None = None
    best_score = -1
    checked: list[str] = []

    for url in candidates:
        status_code, html = await fetch_text(client, url)
        checked.append(f"{url} (status:{status_code})")
        if status_code < 200 or status_code >= 400:
            continue

        status, names_visible, emails_visible, domains, note, title = detect_visibility(html)
        score = (2 if names_visible == "yes" else 0) + (2 if emails_visible == "yes" else 0)
        if score > best_score:
            best_score = score
            best = (url, title, status, names_visible, emails_visible, domains, note)
            if score >= 4:
                break

    if best is None:
        return CrawlResult(
            batch=batch,
            state=row.state,
            priority_order=row.priority_order,
            district_name=row.district_name,
            city=row.city,
            county=row.county,
            staff_directory_url=candidates[0],
            page_title="",
            visibility_status="not_verified_visible",
            names_visible="unknown",
            emails_visible="unknown",
            observed_email_domains="",
            email_pattern_or_note="all candidate URLs failed",
            source_method="automated multi-crawler",
            checked_candidates="; ".join(checked),
        )

    url, title, vis, names, emails, domains, note = best
    return CrawlResult(
        batch=batch,
        state=row.state,
        priority_order=row.priority_order,
        district_name=row.district_name,
        city=row.city,
        county=row.county,
        staff_directory_url=url,
        page_title=title,
        visibility_status=vis,
        names_visible=names,
        emails_visible=emails,
        observed_email_domains=domains,
        email_pattern_or_note=note,
        source_method="automated multi-crawler",
        checked_candidates="; ".join(checked),
    )


def read_rows(path: str, start: int, end: int, state: str) -> list[DistrictRow]:
    rows: list[DistrictRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            if i < start or i > end:
                continue
            rows.append(
                DistrictRow(
                    priority_order=i,
                    district_name=row["District name"].strip(),
                    city=row.get("City", "").strip(),
                    county=row.get("County name", "").strip(),
                    state=state,
                )
            )
    return rows


def write_csv(path: str, results: list[CrawlResult]) -> None:
    fields = list(CrawlResult.__annotations__.keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow(r.__dict__)


def push_to_postgres(connection_string: str, table: str, results: list[CrawlResult]) -> None:
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        batch TEXT NOT NULL,
        state TEXT NOT NULL,
        priority_order INTEGER NOT NULL,
        district_name TEXT NOT NULL,
        city TEXT,
        county TEXT,
        staff_directory_url TEXT,
        page_title TEXT,
        visibility_status TEXT,
        names_visible TEXT,
        emails_visible TEXT,
        observed_email_domains TEXT,
        email_pattern_or_note TEXT,
        source_method TEXT,
        checked_candidates TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (batch, state, priority_order)
    );
    """

    upsert_sql = f"""
    INSERT INTO {table} (
        batch, state, priority_order, district_name, city, county,
        staff_directory_url, page_title, visibility_status, names_visible,
        emails_visible, observed_email_domains, email_pattern_or_note,
        source_method, checked_candidates
    ) VALUES (
        %(batch)s, %(state)s, %(priority_order)s, %(district_name)s, %(city)s, %(county)s,
        %(staff_directory_url)s, %(page_title)s, %(visibility_status)s, %(names_visible)s,
        %(emails_visible)s, %(observed_email_domains)s, %(email_pattern_or_note)s,
        %(source_method)s, %(checked_candidates)s
    )
    ON CONFLICT (batch, state, priority_order) DO UPDATE SET
        district_name = EXCLUDED.district_name,
        city = EXCLUDED.city,
        county = EXCLUDED.county,
        staff_directory_url = EXCLUDED.staff_directory_url,
        page_title = EXCLUDED.page_title,
        visibility_status = EXCLUDED.visibility_status,
        names_visible = EXCLUDED.names_visible,
        emails_visible = EXCLUDED.emails_visible,
        observed_email_domains = EXCLUDED.observed_email_domains,
        email_pattern_or_note = EXCLUDED.email_pattern_or_note,
        source_method = EXCLUDED.source_method,
        checked_candidates = EXCLUDED.checked_candidates;
    """

    with psycopg.connect(connection_string) as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            cur.executemany(upsert_sql, [r.__dict__ for r in results])
        conn.commit()


async def run(args: argparse.Namespace) -> None:
    rows = read_rows(args.input_csv, args.start, args.end, args.state)
    limits = httpx.Limits(max_keepalive_connections=args.concurrency, max_connections=args.concurrency)
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        headers={"User-Agent": "district-research-bot/1.0"},
    ) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def wrapped(r: DistrictRow) -> CrawlResult:
            async with sem:
                return await crawl_one(client, r, args.batch)

        results = await asyncio.gather(*(wrapped(r) for r in rows))

    write_csv(args.output_csv, results)

    if args.postgres_url:
        push_to_postgres(args.postgres_url, args.postgres_table, results)

    print(f"Processed rows: {len(results)}")
    print(f"CSV written: {args.output_csv}")
    if args.postgres_url:
        print(f"Postgres upsert complete: table={args.postgres_table}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Concurrent district staff-directory crawler")
    p.add_argument("--input-csv", required=True, help="Input CSV with District name, City, County name columns")
    p.add_argument("--output-csv", required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--batch", required=True)
    p.add_argument("--state", default="CA")
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--postgres-url", default="", help="Optional PostgreSQL connection string for Neon/local DB")
    p.add_argument("--postgres-table", default="staff_directory_results", help="Target table for upserts")
    asyncio.run(run(p.parse_args()))
