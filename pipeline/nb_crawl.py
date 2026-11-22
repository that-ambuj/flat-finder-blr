"""Polite, cached NoBroker rent crawler for a city's coverage area. Personal use only: output stays local.

usage: python nb_crawl.py <city>  -> out/<city>/nb_listings.json (gitignored)
Reads the server-rendered search pages that robots.txt allows (/flats-for-rent-in-<locality>_<city>?pageNo=N).
"""
import datetime
import gzip
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import nb_parse

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "cache" / "nb"
CITIES = json.loads((ROOT.parent / "data" / "cities.json").read_text())
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY = 2.0
PER_PAGE = 26
MAX_PAGES = 100


def fetch(url):
    """Page HTML, cached per day so a rerun on the same day sends no requests; None on 404."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = f"{datetime.date.today()}|{url}"
    f = CACHE / (hashlib.sha1(key.encode()).hexdigest() + ".html.gz")
    if f.exists():
        return gzip.decompress(f.read_bytes()).decode("utf-8", "ignore")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=40) as resp:
                body = resp.read()
                body = gzip.decompress(body) if resp.headers.get("Content-Encoding") == "gzip" else body
            html = body.decode("utf-8", "ignore")
            f.write_bytes(gzip.compress(html.encode("utf-8"), 9))
            time.sleep(DELAY)
            return html
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(DELAY)
                return None
            print("  retry", attempt + 1, url, e, flush=True)
        except Exception as e:
            print("  retry", attempt + 1, url, e, flush=True)
        time.sleep(5 * (attempt + 1))
    return None


def slug(name):
    return "_".join(name.lower().replace(".", " ").split())


def search_url(locality, nb_city, page):
    return f"{nb_parse.BASE}/flats-for-rent-in-{slug(locality)}_{nb_city}" + (f"?pageNo={page}" if page > 1 else "")


def in_bbox(listing, bbox):
    south, west, north, east = bbox
    return south < listing["lat"] < north and west < listing["lng"] < east


def crawl_locality(locality, nb_city, seen):
    """Walk pageNo until a page is empty. Returns the listings not seen before."""
    found, page, pages = [], 1, None
    while page <= min(pages or MAX_PAGES, MAX_PAGES):
        html = fetch(search_url(locality, nb_city, page))
        records, total = nb_parse.list_page(html) if html else ([], 0)
        pages = pages or -(-total // PER_PAGE)
        if not records:
            break
        fresh = [l for l in map(nb_parse.to_listing, records) if l and l["id"] not in seen]
        seen.update(l["id"] for l in fresh)
        found.extend(fresh)
        page += 1
    print(f"{locality}: {len(found)} new listings from {page - 1} pages (site total {pages * PER_PAGE if pages else 0}~)", flush=True)
    return found


def main(city):
    cfg = CITIES[city]
    cov = cfg.get("coverage") or {}
    nb_city = cfg.get("nobroker")
    if not nb_city:
        sys.exit(f"{city}: no 'nobroker' key in data/cities.json")
    seen, everything = set(), []
    for locality in dict.fromkeys(slug(n) for n in cov.get("localities") or [cfg["name"]]):
        everything.extend(crawl_locality(locality, nb_city, seen))
    bbox = cov.get("bbox") or cfg["bbox"]
    kept = [l for l in everything if in_bbox(l, bbox)]
    out = ROOT / "out" / city
    out.mkdir(parents=True, exist_ok=True)
    (out / "nb_listings.json").write_text(json.dumps({"crawled": str(datetime.date.today()), "listings": kept}, indent=0))
    print(f"collected {len(everything)}, inside coverage {len(kept)} -> {out / 'nb_listings.json'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bangalore")
