import pathlib

import nb_parse

FX = pathlib.Path(__file__).parent / "fixtures"


def page():
    return (FX / "nb_search.html").read_text(encoding="utf-8")


def test_records_span_chunks_and_total():
    records, total = nb_parse.list_page(page())
    assert len(records) == 4 and total == 57


def test_listing_shape():
    listings, _ = nb_parse.listings(page())
    assert listings[0] == {
        "id": "a" * 32, "bhk": 2, "price": 24000, "deposit": 100000, "sqft": 1150, "furnished": "Semi",
        "lat": 12.8401, "lng": 77.6612, "building": "Test Meadows", "locality": "Electronic City", "posted": "2026-11-04",
        "url": "https://www.nobroker.in/property/2-bhk-apartment-for-rent-in-electronic-city-bangalore-for-rs-24000/" + "a" * 32 + "/detail",
        "by": "owner", "source": "NoBroker"}


def test_drops_shared_and_inactive_and_keeps_no_owner_details():
    listings, _ = nb_parse.listings(page())
    assert [l["id"][0] for l in listings] == ["a", "b"]
    assert all("ownerName" not in l and "ownerId" not in l for l in listings)


def test_room_kitchen_has_no_bhk_and_blank_building_is_none():
    rk = nb_parse.listings(page())[0][1]
    assert rk["bhk"] is None and rk["building"] is None


def test_missing_state():
    assert nb_parse.list_page("<html></html>") == ([], 0)
    assert nb_parse.bhk_of("BHK4_PLUS") == 4
