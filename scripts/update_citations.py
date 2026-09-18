#!/usr/bin/env python3
"""
Pulls current Google Scholar stats (citation count, h-index, number of
published papers) for a fixed Scholar profile and writes them to
data/citations.json, which the portfolio site fetches at page-load time.

Two data sources are supported:

1. SerpApi's Google Scholar Author API (preferred, much more reliable).
   Used automatically when a SERPAPI_KEY environment variable / GitHub
   secret is present. Free tier: https://serpapi.com/ (100 searches/month).

2. Direct scraping of the public Scholar profile page (no signup needed,
   but Google occasionally serves a CAPTCHA to automated/datacenter
   traffic like GitHub Actions runners, which makes this less reliable
   over time).

If BOTH sources fail, or return implausible data (zeros / missing
fields), the script deliberately leaves the existing data/citations.json
untouched so the live site never regresses to zero -- it just keeps
showing the last known-good numbers until the next successful run.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SCHOLAR_USER_ID = "sONkdskAAAAJ"  # from the profile URL: ?user=sONkdskAAAAJ
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "citations.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def get_stats_via_serpapi(api_key: str):
    """Fetch stats using SerpApi's google_scholar_author engine."""
    base_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar_author",
        "author_id": SCHOLAR_USER_ID,
        "hl": "en",
        "api_key": api_key,
    }

    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    table = data.get("cited_by", {}).get("table", [])
    citations = h_index = None
    for row in table:
        if "citations" in row:
            citations = row["citations"].get("all")
        if "h_index" in row:
            h_index = row["h_index"].get("all")

    # Count papers by walking SerpApi's pagination until it stops.
    papers = len(data.get("articles", []))
    next_url = data.get("serpapi_pagination", {}).get("next")
    while next_url:
        time.sleep(1)
        page = requests.get(next_url, timeout=30)
        page.raise_for_status()
        page_data = page.json()
        papers += len(page_data.get("articles", []))
        next_url = page_data.get("serpapi_pagination", {}).get("next")

    return {"papers": papers, "h_index": h_index, "citations": citations}


def get_stats_via_scrape():
    """Fetch stats by scraping the public Scholar profile page directly."""
    profile_url = (
        f"https://scholar.google.com/citations?hl=en&user={SCHOLAR_USER_ID}"
    )
    resp = requests.get(profile_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    if "gs_captcha" in resp.text or soup.find(id="gs_captcha_ccl"):
        raise RuntimeError("Blocked by a Google Scholar CAPTCHA challenge")

    rows = soup.select("#gsc_rsb_st tbody tr")
    citations = h_index = None
    for row in rows:
        cells = row.select("td.gsc_rsb_std")
        label = row.select_one("td.gsc_rsb_sc1, a.gsc_rsb_f_at")
        label_text = row.get_text(" ", strip=True).lower()
        if not cells:
            continue
        if label_text.startswith("citations"):
            citations = int(cells[0].get_text(strip=True))
        elif label_text.startswith("h-index"):
            h_index = int(cells[0].get_text(strip=True))

    # Paginate through the publications list to get an exact paper count.
    papers = 0
    cstart = 0
    page_size = 100
    while True:
        page_url = (
            f"https://scholar.google.com/citations?hl=en&user={SCHOLAR_USER_ID}"
            f"&cstart={cstart}&pagesize={page_size}"
        )
        page_resp = requests.get(page_url, headers=HEADERS, timeout=30)
        page_resp.raise_for_status()
        page_soup = BeautifulSoup(page_resp.text, "html.parser")
        rows_on_page = page_soup.select("#gsc_a_b .gsc_a_tr")
        papers += len(rows_on_page)
        if len(rows_on_page) < page_size:
            break
        cstart += page_size
        time.sleep(1.5)

    return {"papers": papers, "h_index": h_index, "citations": citations}


def stats_look_valid(stats: dict) -> bool:
    if not stats:
        return False
    required = ("papers", "h_index", "citations")
    if any(stats.get(k) in (None, 0) for k in required):
        return False
    return True


def main():
    api_key = os.environ.get("SERPAPI_KEY", "").strip()
    stats = None
    source = None

    if api_key:
        try:
            stats = get_stats_via_serpapi(api_key)
            source = "serpapi"
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] SerpApi lookup failed: {exc}", file=sys.stderr)

    if not stats_look_valid(stats):
        try:
            scraped = get_stats_via_scrape()
            if stats_look_valid(scraped):
                stats = scraped
                source = "scholar_scrape"
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] Direct scrape failed: {exc}", file=sys.stderr)

    if not stats_look_valid(stats):
        print(
            "[error] Could not get valid stats from any source this run. "
            "Leaving data/citations.json unchanged.",
            file=sys.stderr,
        )
        # Exit 0 on purpose: a failed refresh should not fail the whole
        # workflow / block other jobs. The site just keeps the old numbers.
        return

    payload = {
        "papers": stats["papers"],
        "h_index": stats["h_index"],
        "citations": stats["citations"],
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": source,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[ok] Wrote {OUTPUT_PATH} via {source}: {payload}")


if __name__ == "__main__":
    main()
