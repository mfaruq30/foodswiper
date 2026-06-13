#!/usr/bin/env python3
"""Generate the Munch app icon as a deterministic 1024x1024 PNG.

Why a generator (not just a committed binary): the icon must be reproducible
and reviewable — a teammate can see *exactly* what the mark is from code, and
regenerate it byte-for-byte. Pure stdlib (zlib + struct) so CI needs nothing
installed; no Pillow, no design tool in the build path.

This is the Phase 6 TestFlight-valid mark: a cream fork on the brand coral
(Theme.accent #E8552E / Theme.paper #FAF6F0). Final art is the Phase 8
design-system deliverable; this exists so an archive passes icon validation
and the app has a coherent, on-brand identity in the meantime.

Run: python tools/make_app_icon.py
Writes: Munch/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 1024
ACCENT = (0xE8, 0x55, 0x2E)  # Theme.accent
CREAM = (0xFA, 0xF6, 0xF0)  # Theme.paper


def _rounded_rect(
    px: float,
    py: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    r_top: float,
    r_bottom: float,
) -> bool:
    """True if (px,py) is inside the rect [x0,x1]x[y0,y1] with rounded corners
    (independent top/bottom radii so a fork tine can round its top only)."""
    if not (x0 <= px <= x1 and y0 <= py <= y1):
        return False
    # Top corners.
    if r_top > 0:
        if px < x0 + r_top and py < y0 + r_top:
            return (px - (x0 + r_top)) ** 2 + (py - (y0 + r_top)) ** 2 <= r_top**2
        if px > x1 - r_top and py < y0 + r_top:
            return (px - (x1 - r_top)) ** 2 + (py - (y0 + r_top)) ** 2 <= r_top**2
    # Bottom corners.
    if r_bottom > 0:
        if px < x0 + r_bottom and py > y1 - r_bottom:
            return (px - (x0 + r_bottom)) ** 2 + (py - (y1 - r_bottom)) ** 2 <= r_bottom**2
        if px > x1 - r_bottom and py > y1 - r_bottom:
            return (px - (x1 - r_bottom)) ** 2 + (py - (y1 - r_bottom)) ** 2 <= r_bottom**2
    return True


def _is_fork(px: float, py: float) -> bool:
    """The cream fork silhouette: four tines -> a merged head -> a handle."""
    cx = SIZE / 2
    # Four tines (rounded tops), width 46, gap 30, centered on cx.
    tine_w, gap = 46.0, 30.0
    span = 4 * tine_w + 3 * gap
    start_x = cx - span / 2
    for i in range(4):
        x0 = start_x + i * (tine_w + gap)
        if _rounded_rect(px, py, x0, 205, x0 + tine_w, 470, r_top=tine_w / 2, r_bottom=0):
            return True
    # Head: solid block joining the tines, rounded at the bottom.
    if _rounded_rect(px, py, start_x, 430, start_x + span, 560, r_top=0, r_bottom=48):
        return True
    # Handle: a rounded vertical bar down to the chin.
    hw = 80.0
    if _rounded_rect(px, py, cx - hw / 2, 540, cx + hw / 2, 858, r_top=20, r_bottom=hw / 2):
        return True
    return False


def render() -> bytes:
    """Raw RGB scanlines (each prefixed with a 0x00 'none' filter byte)."""
    rows = bytearray()
    for y in range(SIZE):
        rows.append(0)
        for x in range(SIZE):
            # Sample at pixel centers so edges land symmetrically.
            rows.extend(CREAM if _is_fork(x + 0.5, y + 0.5) else ACCENT)
    return bytes(rows)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def png_bytes() -> bytes:
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)  # 8-bit RGB
    idat = zlib.compress(render(), 9)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def main() -> None:
    out = (
        Path(__file__).resolve().parent.parent
        / "Munch"
        / "Resources"
        / "Assets.xcassets"
        / "AppIcon.appiconset"
        / "icon-1024.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(png_bytes())
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
