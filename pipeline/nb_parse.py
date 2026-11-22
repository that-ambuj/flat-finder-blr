"""Pure parsers for NoBroker rent search pages (no network).

A search page streams its React state in `self.__next_f.push([1, "<js string>"])` chunks.
The joined chunks hold `"initialProperties": [...]` and `"listPageProperties": {"otherParams": {"total_count": N}}`.
"""
import datetime
import json
import re

_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_BHK = re.compile(r"^BHK(\d+)(?:_PLUS)?$")
BASE = "https://www.nobroker.in"


def stream(html):
    return "".join(json.loads(f'"{s}"') for s in _PUSH.findall(html or ""))


def _value_after(text, key):
    at = text.find(f'"{key}":')
    return json.JSONDecoder().raw_decode(text, at + len(key) + 3)[0] if at >= 0 else None


def list_page(html):
    """(records, total_count) from one search page; ([], 0) when the state is missing."""
    text = stream(html)
    # listPageProperties.data is only a "$f:..." reference string. The records are in initialProperties.
    records = _value_after(text, "initialProperties")
    meta = _value_after(text, "listPageProperties") or {}
    return (records if isinstance(records, list) else []), (meta.get("otherParams") or {}).get("total_count") or 0


def bhk_of(kind):
    m = _BHK.match(kind or "")
    return int(m.group(1)) if m else None


def _num(v):
    return v if isinstance(v, (int, float)) and v > 0 else None


def _posted(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).date().isoformat() if _num(ms) else None


def to_listing(r):
    """One rent listing in the pipeline's shape, or None for inactive, shared or lease-only records."""
    if not r.get("active", True) or r.get("sharedAccomodation") or r.get("forLease"):
        return None
    lat, lng = _num(r.get("latitude")), _num(r.get("longitude"))
    if not (r.get("id") and _num(r.get("rent")) and lat and lng):
        return None
    building = (r.get("buildingName") or "").strip() or None
    return {"id": r["id"], "bhk": bhk_of(r.get("type")), "price": r["rent"], "deposit": _num(r.get("deposit")),
            "sqft": _num(r.get("propertySize")), "furnished": r.get("furnishingDesc") or None,
            "lat": lat, "lng": lng, "building": building, "locality": r.get("locality") or None,
            "posted": _posted(r.get("activationDate")), "url": BASE + r["detailUrl"] if r.get("detailUrl") else None,
            "by": "owner", "source": "NoBroker"}


def listings(html):
    records, total = list_page(html)
    return [l for l in map(to_listing, records) if l], total
