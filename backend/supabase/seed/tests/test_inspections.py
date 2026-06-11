"""Record parsers, pinned to the REAL portal field shapes (verified 2026-06-11).

The first live Boston run returned 0 records because the parser expected a
`licenseno` field the dataset does not have — these tests exist so a portal
schema change breaks loudly here instead of silently zeroing the fetch.
"""

from munch_seed.inspections import _boston_record, _nyc_record

BOSTON_ROW: dict[str, object] = {
    "_id": 1,
    "businessname": "100 Federal Market & Barista- 10th Floor",
    "dbaname": None,
    "address": "100 Federal",
    "city": "Boston",
    "licstatus": "Active",
    "licensecat": "FS",
    "descript": "Eating & Drinking",
    "license_add_dt_tm": "2023-08-09 16:00:26.99+00",
    "property_id": "57150",
    "latitude": "42.354770000088834",
    "longitude": "-71.0561300019333",
}


def test_boston_real_shape_parses() -> None:
    rec = _boston_record(BOSTON_ROW)
    assert rec is not None
    assert rec.ref == "57150:FS:100federalmarketbarista10thfloor"
    assert rec.name == "100 Federal Market & Barista- 10th Floor"
    assert abs(rec.lat - 42.35477) < 1e-4
    assert rec.last_seen == "2023-08-09 16:00:26.99+00"


def test_boston_dba_preferred_over_legal_name() -> None:
    rec = _boston_record({**BOSTON_ROW, "dbaname": "Federal Cafe"})
    assert rec is not None
    assert rec.name == "Federal Cafe"
    assert rec.ref.endswith(":federalcafe")  # ref follows the public-facing name


def test_boston_inactive_or_unlocatable_rows_drop() -> None:
    assert _boston_record({**BOSTON_ROW, "licstatus": "Inactive"}) is None
    assert _boston_record({**BOSTON_ROW, "latitude": None}) is None
    assert _boston_record({**BOSTON_ROW, "latitude": "0", "longitude": "0"}) is None
    assert _boston_record({**BOSTON_ROW, "property_id": ""}) is None


def test_nyc_record_parses_and_rejects_ungecoded() -> None:
    row = {
        "camis": "41000000",
        "dba": "JOE'S PIZZA",
        "latitude": "40.7305",
        "longitude": "-74.0021",
        "cuisine_description": "Pizza",
        "last_inspection": "2026-04-01T00:00:00.000",
    }
    rec = _nyc_record(row)
    assert rec is not None
    assert rec.ref == "41000000"
    assert rec.cuisine_description == "Pizza"
    assert _nyc_record({**row, "latitude": "0", "longitude": "0"}) is None
    assert _nyc_record({**row, "dba": ""}) is None
