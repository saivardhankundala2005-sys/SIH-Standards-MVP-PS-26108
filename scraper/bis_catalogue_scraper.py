"""
Scrapes IS-number / title / sector metadata from the BIS sector-wise catalogue
(https://standards.bis.gov.in/website/catalogue-list) so we know WHAT to
download and how to tag it, before we go fetch actual PDF text.

Run: python -m scraper.bis_catalogue_scraper --out data/catalogue.json

NOTE for the hackathon demo: BIS does not publish a stable public JSON API for
this page, and structure can change. This scraper is intentionally defensive
(try/except per row, rate-limited) and should be re-checked against the live
HTML before the final demo. If BIS blocks scraping in your network, fall back
to manually exporting a sector's list from "Know Your Standard" search results
and feed that CSV into ingestion instead (see data/catalogue_manual_template.csv).
"""
import argparse
import json
import time
from dataclasses import dataclass, asdict
from typing import List

import requests
from bs4 import BeautifulSoup

CATALOGUE_URL = "https://standards.bis.gov.in/website/catalogue-list"
HEADERS = {"User-Agent": "SIH-PS26108-ResearchBot/1.0 (contact: your-email@example.com)"}
REQUEST_DELAY_SECONDS = 1.5  # be polite


@dataclass
class StandardMeta:
    is_number: str
    title: str
    sector: str
    year: str = ""
    status: str = "active"  # active | withdrawn | superseded
    source_url: str = CATALOGUE_URL


def fetch_sectors() -> List[str]:
    """Fetch the list of sector names/ids from the catalogue landing page."""
    resp = requests.get(CATALOGUE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    sectors = [a.get_text(strip=True) for a in soup.select("a.sector-link")]
    if not sectors:
        # Structure differs from what we expect — surface this loudly instead
        # of silently returning nothing.
        raise RuntimeError(
            "No sector links found with selector 'a.sector-link'. "
            "Inspect the live page HTML and update the CSS selector."
        )
    return sectors


def fetch_standards_for_sector(sector_name: str, sector_url: str) -> List[StandardMeta]:
    resp = requests.get(sector_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cells) < 2:
            continue
        try:
            is_number, title = cells[0], cells[1]
            year = cells[2] if len(cells) > 2 else ""
            results.append(StandardMeta(is_number=is_number, title=title,
                                         sector=sector_name, year=year,
                                         source_url=sector_url))
        except Exception as e:
            print(f"[warn] skipping malformed row in {sector_name}: {e}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/catalogue.json")
    args = parser.parse_args()

    all_standards: List[StandardMeta] = []
    try:
        sectors = fetch_sectors()
    except Exception as e:
        print(f"[error] {e}\nFalling back to manual CSV workflow — see docstring.")
        return

    for sector in sectors:
        print(f"Fetching sector: {sector}")
        try:
            all_standards.extend(fetch_standards_for_sector(sector, CATALOGUE_URL))
        except Exception as e:
            print(f"[warn] failed sector {sector}: {e}")
        time.sleep(REQUEST_DELAY_SECONDS)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in all_standards], f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(all_standards)} standards to {args.out}")


if __name__ == "__main__":
    main()
