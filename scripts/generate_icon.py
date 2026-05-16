"""Generate scripts/financial-assistant.ico from the donut-ring logo.

Draws the same shape as frontend/public/favicon.svg (thin ring + a 90-degree
wedge) at four resolutions and packs them into a single multi-resolution ICO
suitable for Windows shortcuts and the installer .exe.

Run once after changing the logo:
    backend/.venv/Scripts/python.exe scripts/generate_icon.py
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "financial-assistant.ico"
SIZES = [16, 32, 48, 64, 128, 256]

# Solid icon color. Picked to read clearly on both light and dark Windows
# taskbars; near-black with a faint blue tint mirrors the light-theme primary.
COLOR = (15, 15, 18, 255)


def _draw(size: int) -> Image.Image:
    """Render the donut-ring logo at ``size`` x ``size`` px."""
    # 4x supersample for smoother circles, then downsample.
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Geometry matches viewBox="0 0 32 32" from favicon.svg, scaled.
    # Ring: cx=16, cy=16, r=12, stroke-width=3 -> outer r=13.5, inner r=10.5.
    cx, cy = s / 2, s / 2
    r = 12 / 32 * s
    sw = 3 / 32 * s
    outer = r + sw / 2
    inner = r - sw / 2

    # Outer ring (annulus).
    draw.ellipse(
        [cx - outer, cy - outer, cx + outer, cy + outer],
        fill=COLOR,
    )
    draw.ellipse(
        [cx - inner, cy - inner, cx + inner, cy + inner],
        fill=(0, 0, 0, 0),
    )

    # Wedge: filled pie slice from 12 o'clock to 3 o'clock (90 degrees),
    # inner-cut to leave just the wedge thickness.
    # Pillow draw.pieslice uses 0 = right (3 o'clock), 90 = bottom. We want
    # 12 -> 3 o'clock, which is -90 to 0 in Pillow's coords.
    draw.pieslice(
        [cx - outer, cy - outer, cx + outer, cy + outer],
        start=-90, end=0,
        fill=COLOR,
    )
    # Cut the inner hole so the wedge is the same thickness as the ring,
    # leaving only the band between r-sw/2 and r+sw/2 visible.
    # Actually the SVG path fills the wedge solidly (no inner cut), so the
    # wedge looks chunkier than the ring. Match that for fidelity.

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    # Render the largest size once and let PIL resample down for the smaller
    # frames in the ICO. Passing append_images with multiple frames keeps only
    # the first one; sizes= is the supported way to multi-resolution an ICO.
    base = _draw(max(SIZES))
    base.save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Wrote {OUT}  ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
