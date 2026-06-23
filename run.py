"""
JobWatch runner.

Launches a headless browser, runs each site scraper, applies the keyword
match (pripravnik, case-insensitive), filters out anything already seen,
and fires notifications for what's new.

Add ljekarne as a second scraper once its flow is defined — just import it
and append to SCRAPERS below; everything downstream (match/dedup/notify)
already works for any Job list.

Run:  python run.py
Env:  HEADLESS=0 to watch the browser while debugging.
"""
import os
import sys
from playwright.sync_api import sync_playwright

from sites import hzz, ljekarne
from store import filter_new
from notify import notify

KEYWORD = "JOUKHADAR"          # matched case-insensitively
SCRAPERS = [hzz.scrape, ljekarne.scrape]   # both sites; matches merge into one email


def matches(job) -> bool:
    return KEYWORD.lower() in (job.text or "").lower()


def main() -> int:
    headless = os.getenv("HEADLESS", "1") != "0"
    all_jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            locale="hr-HR",
        )
        page = ctx.new_page()

        for scrape in SCRAPERS:
            try:
                all_jobs.extend(scrape(page))
            except Exception as e:
                print(f"[warn] {scrape.__module__} failed: {e}", file=sys.stderr)

        browser.close()

    matched = [j for j in all_jobs if matches(j)]
    print(f"scraped={len(all_jobs)} matched_keyword={len(matched)}")

    fresh = filter_new(matched)
    print(f"new (not seen before)={len(fresh)}")

    if fresh:
        for status in notify(fresh):
            print(status)
        for j in fresh:
            print(f"  NEW: {j.title} | {j.location} | {j.employer} | {j.url}")
    else:
        print("nothing new to alert")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
