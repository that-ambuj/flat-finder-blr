"""Polite, cached, resumable Magicbricks crawler.

usage: python mb_crawl.py list <city>      # all list pages -> out/<city>/mb_index.json
       python mb_crawl.py projects <city>  # every project page -> out/<city>/mb_projects.json
<city> is a key in data/cities.json (default gurgaon).
"""
import gzip
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

import mb_parse

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "cache" / "mb"
OUT = ROOT / "out"
CITIES = json.loads((ROOT.parent / "data" / "cities.json").read_text())
CITY = next((a for a in sys.argv[1:] if a in CITIES), "gurgaon")
CFG = CITIES[CITY]
LIST_URL = "https://www.magicbricks.com/residential-projects-in-" + CFG["magicbricks"] + "-nprid/page-{}"
OUT = OUT / CITY
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY = 1.0


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html.gz")
    if f.exists() and f.stat().st_size > 2000:
        return gzip.decompress(f.read_bytes()).decode("utf-8", "ignore")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
            f.write_bytes(gzip.compress(html.encode("utf-8"), 9))
            time.sleep(DELAY)
            return html
        except Exception as e:  # network hiccup: back off and retry
            print("  retry", attempt + 1, url, e, flush=True)
            time.sleep(5 * (attempt + 1))
    return None


def crawl_list():
    from concurrent.futures import ThreadPoolExecutor

    first = fetch(LIST_URL.format(1))
    total = mb_parse.parse_total(first)
    pages = -(-total // 20)

    def one(n):
        html = fetch(LIST_URL.format(n))
        return [mb_parse.card_to_project(c) for c in mb_parse.parse_list_page(html)] if html else []

    with ThreadPoolExecutor(max_workers=3) as ex:
        projects = {}
        for n, cards in enumerate(ex.map(one, range(1, pages + 1)), 1):
            projects.update({c["mb_id"]: c for c in cards})
            if n % 50 == 0 or n == pages:
                print(f"list {n}/{pages}: {len(projects)} projects", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mb_index.json").write_text(json.dumps(list(projects.values()), indent=0))
    print("total reported", total, "collected", len(projects))


def in_coverage(project, cfg):
    names = (cfg.get("coverage") or {}).get("localities")
    locality = (project.get("locality") or "").lower()
    return not names or any(n.lower() in locality for n in names)


def crawl_projects():
    index = [p for p in json.loads((OUT / "mb_index.json").read_text()) if in_coverage(p, CFG)]
    print("projects in coverage", len(index), flush=True)
    from concurrent.futures import ThreadPoolExecutor

    def one(p):
        html = fetch(p["url"])
        try:
            detail = mb_parse.parse_project_page(html) if html else {}
        except Exception as e:
            print("  parse failed", p["url"], e, flush=True)
            detail = {}
        return {**p, **{k: v for k, v in detail.items() if v not in (None, [], "")}}

    out = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, merged in enumerate(ex.map(one, index), 1):
            out.append(merged)
            if i % 100 == 0 or i == len(index):
                print(f"project {i}/{len(index)}", flush=True)
                (OUT / "mb_projects.json").write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    {"list": crawl_list, "projects": crawl_projects}[sys.argv[1]]()
