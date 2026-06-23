"""
HZZ (burzarada.hzz.hr) scraper using Playwright.

Flow (all steps are ASP.NET __doPostBack postbacks — we wait for each to settle):
  1. Open Posloprimac_RadnaMjesta.aspx
  2. Click "Županije" toggle to reveal the county list
  3. Select the county radio (value="15" = Splitsko-dalmatinska)
  4. Type the search term into #txtSearch
  5. Click #btnSearch
  6. Parse every result card

Returns a list of Job dicts. Match logic (pripravnik / case-insensitive) is applied
by the caller against each job's `text` field.
"""

from dataclasses import dataclass, field
from playwright.sync_api import Page, TimeoutError as PWTimeout

URL = "https://burzarada.hzz.hr/Posloprimac_RadnaMjesta.aspx"

# Splitsko-dalmatinska županija radio value (from your HTML: rblZupanija_15, value="15")
ZUPANIJA_VALUE = "15"
SEARCH_TERM = "farmaceutski"


@dataclass
class Job:
    site: str
    job_id: str          # WebSifra — stable dedup key
    title: str
    location: str = ""
    employer: str = ""
    deadline: str = ""
    url: str = ""
    text: str = ""       # full card text, used for keyword matching


def _settle(page: Page, timeout: int = 20000):
    """Wait for an ASP.NET postback to finish re-rendering the grid."""
    # networkidle catches the async postback; the results container confirms the grid is back.
    page.wait_for_load_state("networkidle", timeout=timeout)


def scrape(page: Page) -> list[Job]:
    page.goto(URL, wait_until="networkidle", timeout=30000)

    # --- Step 1: open the Županije panel -------------------------------------
    # The toggle: <a ... data-action="toggle" data-side="left" ...>Županije</a>
    zup_toggle = page.locator('a[data-action="toggle"][data-side="left"]')
    zup_toggle.first.click()
    # This one is a client-side slide-out panel (no postback), so a short wait is enough.
    page.wait_for_timeout(500)

    # --- Step 2: select the county radio (triggers a postback) ---------------
    # <input id="ctl00_MainContent_rblZupanija_15" type="radio" value="15" ...>
    radio = page.locator(f'#ctl00_MainContent_rblZupanija_{ZUPANIJA_VALUE}')
    radio.wait_for(state="visible", timeout=10000)
    radio.check()           # the onclick fires __doPostBack via setTimeout
    _settle(page)           # wait for the postback to re-render

    # --- Step 3: type the search term ----------------------------------------
    search_box = page.locator('#txtSearch')
    search_box.wait_for(state="visible", timeout=10000)
    search_box.fill("")     # clear any residual value
    search_box.fill(SEARCH_TERM)

    # --- Step 4: click search (postback) -------------------------------------
    # <a id="btnSearch" href="javascript:__doPostBack('...btnSearch','')" ...>
    page.locator('#btnSearch').click()
    _settle(page)

    # --- Step 5: parse cards -------------------------------------------------
    return _parse_cards(page)


def _parse_cards(page: Page) -> list[Job]:
    jobs: list[Job] = []
    # Each result's title anchor; the card is its ancestor .row
    titles = page.locator('a.TitleLink')
    count = titles.count()

    for i in range(count):
        a = titles.nth(i)
        href = a.get_attribute("href") or ""
        # WebSifra=164304299  -> stable id
        job_id = ""
        if "WebSifra=" in href:
            job_id = href.split("WebSifra=")[1].split("&")[0]

        title = (a.inner_text() or "").strip()

        # Walk up to the surrounding card (.row) and grab its full text for matching
        card = a.locator(
            'xpath=ancestor::div[contains(@class,"row")][1]'
        )
        card_text = ""
        try:
            card_text = card.inner_text(timeout=2000)
        except PWTimeout:
            card_text = title

        # Pull the labelled spans where present (ids contain a per-row ctlNN segment,
        # so we locate them by suffix within this card)
        def span_by_suffix(suffix: str) -> str:
            loc = card.locator(f'span[id$="{suffix}"]')
            try:
                if loc.count():
                    return (loc.first.inner_text() or "").strip()
            except PWTimeout:
                pass
            return ""

        location = span_by_suffix("MjeNazivLabel")
        employer = span_by_suffix("PosNazivLabel")
        deadline = span_by_suffix("RadMjeRokPrijaveLabel")

        full_url = "https://burzarada.hzz.hr/" + href if href else URL

        jobs.append(Job(
            site="hzz",
            job_id=job_id or full_url,
            title=title,
            location=location,
            employer=employer,
            deadline=deadline,
            url=full_url,
            text=card_text,
        ))

    return jobs
