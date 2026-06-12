"""Geohash encoding for the Firestore writer.

An intentional independent copy of the encoder in backend/reco/app/geohash.py
(same rationale as geo.py: separate packages, separate venvs, no runtime
coupling). The reco side additionally owns the query-bounds logic; the seed
side only ever needs encode-at-write-time. If the algorithm is ever tuned,
change both deliberately — precision MUST stay identical or range queries
against seeded data will silently miss venues.
"""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

ENCODE_PRECISION = 9  # MUST match app/geohash.py ENCODE_PRECISION


def encode(lat: float, lon: float, precision: int = ENCODE_PRECISION) -> str:
    """Standard geohash base32 encoding."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    out: list[str] = []
    bit, ch, even = 0, 0, True
    while len(out) < precision:
        if even:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                ch = (ch << 1) | 1
                lon_lo = mid
            else:
                ch <<= 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                ch = (ch << 1) | 1
                lat_lo = mid
            else:
                ch <<= 1
                lat_hi = mid
        even = not even
        bit += 1
        if bit == 5:
            out.append(_BASE32[ch])
            bit, ch = 0, 0
    return "".join(out)
