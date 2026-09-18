"""
Downloads standard PDFs given a catalogue.json (from bis_catalogue_scraper or
the manual CSV). Point PRODUCT_MANUALS_URL scraping at
https://www.bis.gov.in/product-certification/product-specific-information-2/product-manuals-copy/
to get direct PDF links for ~800 pre-compiled product manuals.

Run: python -m scraper.pdf_downloader --catalogue data/catalogue.json --out storage/pdfs/
"""
import argparse
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "SIH-PS26108-ResearchBot/1.0 (contact: your-email@example.com)"}
PRODUCT_MANUALS_URL = (
    "https://www.bis.gov.in/product-certification/"
    "product-specific-information-2/product-manuals-copy/"
)
REQUEST_DELAY_SECONDS = 1.5


def discover_product_manual_pdf_links() -> list[dict]:
    resp = requests.get(PRODUCT_MANUALS_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            links.append({"title": a.get_text(strip=True), "url": href})
    return links


def download(url: str, dest: Path):
    resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue", default="data/catalogue.json")
    parser.add_argument("--out", default="storage/pdfs")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Discovering product-manual PDF links...")
    try:
        manual_links = discover_product_manual_pdf_links()
    except Exception as e:
        print(f"[warn] could not discover product manuals: {e}")
        manual_links = []

    for link in manual_links:
        safe_name = "".join(c for c in link["title"] if c.isalnum() or c in " _-")[:120]
        dest = out_dir / f"{safe_name}.pdf"
        if dest.exists():
            continue
        try:
            print(f"Downloading: {link['title']}")
            download(link["url"], dest)
        except Exception as e:
            print(f"[warn] failed {link['url']}: {e}")
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Done. PDFs in {out_dir}")
    print("Tip: for standards not in product manuals, use the 'Know Your "
          "Standard' portal search UI manually (BIS requires registration/"
          "captcha for individual IS PDF downloads, so this can't be fully "
          "automated within hackathon time — mention this as a manual step "
          "or an official-API integration ask in your pitch).")


if __name__ == "__main__":
    main()
