"""
Ljekarne SDŽ (ljekarnasdz.hr) scraper using Playwright.

Page 1 of /natjecajizaposao lists job postings as cards:
  div.news-promo__item-block        (wrapper, carries the date)
    div.news-promo__date            (day / month / year spans)
    div.news-promo__content
      h2.news-promo__title > a      (title + stable URL slug = dedup key)

Match logic ('pripravnik', case-insensitive) is applied by the caller
against each job's `text` field, which here is the card title.

Server-rendered, but we use the same Playwright page for consistency with
the HZZ flow (one browser context drives both sites).
"""
from playwright.sync_api import Page, TimeoutError as PWTimeout

# Import Job from the hzz module so both sites share one dataclass.
from .hzz import Job

URL = "https://www.ljekarnasdz.hr/natjecajizaposao"


def scrape(page: Page) -> list[Job]:
    page.goto(URL, wait_until="networkidle", timeout=30000)

    jobs: list[Job] = []

    # Title anchors inside each card. We key off these and walk up for the date.
    titles = page.locator("h2.news-promo__title a")
    try:
        titles.first.wait_for(state="visible", timeout=10000)
    except PWTimeout:
        # No cards found (layout change or empty page) — return nothing rather than crash.
        return jobs

    count = titles.count()
    for i in range(count):
        a = titles.nth(i)
        href = (a.get_attribute("href") or "").strip()
        title = (a.inner_text() or "").strip()

        # Stable dedup id = the posting slug (last path segment of the href)
        job_id = href.rstrip("/").split("/")[-1] if href else title

        # Walk up to the item-block wrapper to grab the date, if present
        deadline = ""
        try:
            block = a.locator(
                'xpath=ancestor::div[contains(@class,"news-promo__item-block")][1]'
            )
            if block.count():
                d = block.locator(".news-promo__date-day")
                m = block.locator(".news-promo__date-month")
                y = block.locator(".news-promo__date-year")
                parts = []
                for loc in (d, m, y):
                    if loc.count():
                        parts.append((loc.first.inner_text() or "").strip())
                deadline = "".join(parts)  # e.g. "17.06.26."
        except PWTimeout:
            pass

        jobs.append(Job(
            site="ljekarnesdz",
            job_id=job_id,
            title=title,
            location="",            # not shown on the card
            employer="Ljekarne SDŽ",
            deadline=deadline,       # this is the posting date, not an application deadline
            url=href or URL,
            text=title,              # match 'pripravnik' against the title
        ))

    return jobs
