"""Fetch establishment records from the NYC and Boston open-data portals.

Both fetchers return InspectionRecord lists; network access happens only at
seed/re-sync time, never at serve time (spec §6.4).
"""

import httpx

from .config import BOSTON_CKAN_API, BOSTON_LICENSES_DATASET, NYC_SOCRATA_URL
from .records import InspectionRecord

_PAGE = 5_000
_TIMEOUT = httpx.Timeout(60.0)


def fetch_nyc(client: httpx.Client | None = None) -> list[InspectionRecord]:
    """NYC DOHMH inspections, deduped to one row per establishment (CAMIS).

    The dataset is violation-level (~300k rows); SoQL group-by collapses it
    server-side to unique establishments with their latest inspection date.
    """
    own_client = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    records: dict[str, InspectionRecord] = {}
    try:
        offset = 0
        while True:
            params = {
                "$select": (
                    "camis, dba, latitude, longitude, cuisine_description,"
                    " max(inspection_date) as last_inspection"
                ),
                "$group": "camis, dba, latitude, longitude, cuisine_description",
                "$limit": str(_PAGE),
                "$offset": str(offset),
            }
            rows = http.get(NYC_SOCRATA_URL, params=params).raise_for_status().json()
            if not rows:
                break
            for row in rows:
                rec = _nyc_record(row)
                if rec is None:
                    continue
                # Group-by can split one CAMIS across name/coord variants;
                # keep the most recently inspected variant.
                existing = records.get(rec.ref)
                if existing is None or (rec.last_seen or "") > (existing.last_seen or ""):
                    records[rec.ref] = rec
            offset += _PAGE
    finally:
        if own_client:
            http.close()
    return list(records.values())


def _nyc_record(row: dict[str, str]) -> InspectionRecord | None:
    camis, name = row.get("camis"), row.get("dba")
    lat, lon = row.get("latitude"), row.get("longitude")
    if not (camis and name and lat and lon):
        return None
    try:
        lat_f, lon_f = float(lat), float(lon)
    except ValueError:
        return None
    if lat_f == 0.0 and lon_f == 0.0:
        return None  # DOHMH uses 0,0 for un-geocoded rows
    return InspectionRecord(
        source="nyc_open_data",
        ref=camis,
        name=name,
        lat=lat_f,
        lon=lon_f,
        cuisine_description=row.get("cuisine_description"),
        last_seen=row.get("last_inspection"),
    )


def fetch_boston(client: httpx.Client | None = None) -> list[InspectionRecord]:
    """Analyze Boston ACTIVE food-establishment licenses (~3.3k rows).

    The resource id is resolved from the dataset slug at call time so a portal
    re-upload (which rotates resource ids) cannot silently break the pipeline.
    """
    own_client = client is None
    http = client or httpx.Client(timeout=_TIMEOUT)
    try:
        meta = (
            http.get(f"{BOSTON_CKAN_API}/package_show", params={"id": BOSTON_LICENSES_DATASET})
            .raise_for_status()
            .json()
        )
        resources = meta["result"]["resources"]
        resource_id = next(
            r["id"] for r in resources if r.get("datastore_active") or r.get("format") == "CSV"
        )

        records: list[InspectionRecord] = []
        offset = 0
        while True:
            payload = (
                http.get(
                    f"{BOSTON_CKAN_API}/datastore_search",
                    params={"resource_id": resource_id, "limit": str(_PAGE), "offset": str(offset)},
                )
                .raise_for_status()
                .json()
            )
            rows = payload["result"]["records"]
            if not rows:
                break
            records.extend(rec for row in rows if (rec := _boston_record(row)) is not None)
            offset += _PAGE
        return records
    finally:
        if own_client:
            http.close()


def _boston_record(row: dict[str, object]) -> InspectionRecord | None:
    license_no = str(row.get("licenseno") or "").strip()
    # Boston splits identity across businessname/dbaname; prefer the DBA the
    # public actually sees, falling back to the legal name.
    name = str(row.get("dbaname") or row.get("businessname") or "").strip()
    lat_raw, lon_raw = row.get("latitude"), row.get("longitude")
    if not (license_no and name and lat_raw and lon_raw):
        return None
    try:
        lat_f, lon_f = float(str(lat_raw)), float(str(lon_raw))
    except ValueError:
        return None
    if lat_f == 0.0 and lon_f == 0.0:
        return None
    return InspectionRecord(
        source="boston_open_data",
        ref=license_no,
        name=name,
        lat=lat_f,
        lon=lon_f,
        cuisine_description=None,  # Boston's dataset has no cuisine field (D-011)
        last_seen=str(row.get("issdttm") or "") or None,
    )
