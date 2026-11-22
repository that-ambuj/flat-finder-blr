import json
import pathlib

import build_city
import geo


def area(name, center, r=150):
    return {"type": "Feature", "properties": {"osm": "way/" + name, "name": name},
            "geometry": {"type": "Polygon", "coordinates": [geo.circle(center, r)]}}


def test_match_area_inside_and_by_name():
    areas = [area("Heritage One", (77.0891, 28.4027)), area("Skyon", (77.0966, 28.3995))]
    g = build_city.Grid(areas, lambda a: geo.centroid(a["geometry"]["coordinates"][0]))
    p = {"name": "Conscient Heritage One", "lng": 77.0893, "lat": 28.4030}
    assert build_city.match_area(p, g)["properties"]["name"] == "Heritage One"
    near = {"name": "Ireo Skyon", "lng": 77.0966 + 0.0025, "lat": 28.3995}  # ~245 m east, outside
    assert build_city.match_area(near, g)["properties"]["name"] == "Skyon"
    far = {"name": "Random Homes", "lng": 77.2, "lat": 28.5}
    assert build_city.match_area(far, g) is None


def test_dedupe_merges_phases_close_by():
    a = {"name": "Heritage One", "lng": 77.0890, "lat": 28.4034, "url": "a"}
    b = {"name": "Heritage One", "lng": 77.0891, "lat": 28.4021, "url": "b"}
    c = {"name": "Heritage One", "lng": 77.2, "lat": 28.5, "url": "c"}
    out = build_city.dedupe([a, b, c])
    assert len(out) == 2 and out[0]["merged"] == ["b"]


def test_kind_of():
    assert build_city.kind_of({"config_text": "2, 3, 4 BHK Multistorey Apartments"}) == "apartment"
    assert build_city.kind_of({"config_text": "Residential Plot"}) == "plot"
    assert build_city.kind_of({"config_text": "4 BHK Villa"}) == "villa"


def test_neighbourhood_sized_area_is_not_a_society_site():
    big = area("DLF Phase 4", (77.08, 28.46), r=700)  # ~1.5 km2
    g = build_city.Grid([big], lambda a: geo.centroid(a["geometry"]["coordinates"][0]))
    p = {"name": "Some Apartments", "lng": 77.08, "lat": 28.46, "acres": 5}
    assert build_city.match_area(p, g) is None


def test_kind_from_unit_codes_when_text_missing():
    assert build_city.kind_of({"configs": {"units": [{"kind": "10000"}]}}) == "plot"
    assert build_city.kind_of({"configs": {"units": [{"kind": "10008"}, {"kind": "10002"}]}}) == "apartment"
    assert build_city.kind_of({}) == "apartment~"


def test_kind_from_card_type_codes():
    assert build_city.kind_of({"type_codes": ["10000"]}) == "plot"
    assert build_city.kind_of({"card_units": [{"kind": "10003", "bhk": 3, "sqft": 1900.0}]}) == "builder floor"


def test_infer_kind_from_name():
    assert build_city.kind_of({"name": "Sai Ram Apartment"}) == "apartment~"
    assert build_city.kind_of({"name": "Rzone Land Plot"}) == "plot~"
    assert build_city.kind_of({"name": "Emaar Business District 114"}) == "commercial~"
    assert build_city.kind_of({"name": "Ashiana Villas"}) == "villa~"


def test_match_verified_needs_whole_name_and_sector():
    ps = [{"mb_id": 1, "name": "M3M", "locality": "Sector 65"},
          {"mb_id": 2, "name": "M3M Heights", "locality": "Sector 65"},
          {"mb_id": 3, "name": "M3M St Andrews at SCDA", "locality": "Sector 113"},
          {"mb_id": 4, "name": "M3M St. Andrews", "locality": "Sector 65"}]
    assert build_city.match_verified({"match": ["M3M Heights"], "sector": "65"}, ps)["mb_id"] == 2
    assert build_city.match_verified({"match": ["M3M St Andrews"], "sector": "65"}, ps)["mb_id"] == 4
    assert build_city.match_verified({"match": ["M3M Heights"], "sector": "65"}, ps, taken={2}) is None


def test_within_bounds_uses_coverage_then_bounds_then_bbox():
    cities = json.loads((pathlib.Path(build_city.ROOT).parent / "data" / "cities.json").read_text())
    sohna = {"lat": 28.2837, "lng": 77.0653}
    assert build_city.within_bounds([sohna], cities["gurgaon"]) == [sohna]
    ecity = {"lat": 12.8452, "lng": 77.6602}
    koramangala = {"lat": 12.9352, "lng": 77.6245}
    assert build_city.within_bounds([ecity, koramangala, {"lat": None, "lng": None}], cities["bangalore"]) == [ecity]


def nb_listing(building, lng, lat, bhk=2, price=25000):
    return {"id": building, "bhk": bhk, "price": price, "deposit": 1e5, "sqft": 1100, "furnished": "Semi", "posted": "2026-11-01",
            "url": "u", "lat": lat, "lng": lng, "building": building, "by": "owner", "source": "NoBroker"}


def test_merge_nobroker_by_name_tokens_within_400m():
    near = {"name": "Ittina Mahavir", "lng": 77.6482, "lat": 12.8402}
    other = {"name": "Prime City", "lng": 77.6500, "lat": 12.8410}
    projects = [near, other]
    listings = [nb_listing("Ittina Mahavir", 77.6485, 12.8404),
                nb_listing("Ittina Mahavir", 77.6800, 12.8402),
                nb_listing("Sai Nilayam", 77.6483, 12.8402),
                nb_listing(None, 77.6483, 12.8402),
                nb_listing("Ittina Mahavir", 77.6483, 12.8402, bhk=None)]
    assert build_city.merge_nobroker(projects, listings) == (1, 4)
    assert near["rent_listings"][0]["source"] == "NoBroker" and "lat" not in near["rent_listings"][0]
    assert near["nobroker"][0]["price"] == 25000 and "rent_listings" not in other


def test_merge_nobroker_prefers_more_shared_tokens():
    a = {"name": "SJR Parkway Homes", "lng": 77.66, "lat": 12.85}
    b = {"name": "Parkway Villas", "lng": 77.6601, "lat": 12.85}
    build_city.merge_nobroker([a, b], [nb_listing("SJR Parkway Homes", 77.6601, 12.8501)])
    assert a.get("rent_listings") and not b.get("rent_listings")


def test_merge_nobroker_same_name_spaces_ignored_up_to_2km():
    p = {"name": "Kolte Patil I Towers Exente", "lng": 77.66, "lat": 12.85}
    far = {"name": "Godrej Nurture", "lng": 77.66, "lat": 12.80}
    listings = [nb_listing("Kolte Patil Itowers Exente", 77.66, 12.8640), nb_listing("Godrej Nurture", 77.66, 12.8290)]
    assert build_city.merge_nobroker([p, far], listings) == (1, 1)
