"""Albedo, legends and packed linear material maps for the DG forward console."""

import io
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 2048, 1024
FONT = Path(__file__).resolve().parents[3] / "Extern/imgui/Lekton-Bold.ttf"
# sRGB colour, linear roughness, linear metal fraction.
FINISHES = {
    "padding": ((48, 51, 51), 0.89, 0.015),
    "gasket": ((33, 35, 36), 0.91, 0.01),
    "rail": ((103, 112, 116), 0.42, 0.62),
    "fastener": ((140, 147, 145), 0.31, 0.78),
    "fascia": ((86, 101, 109), 0.66, 0.18),
    "bezel": ((66, 76, 84), 0.55, 0.31),
}


def swatch(finish):
    return (64 + 128 * list(FINISHES).index(finish)) / W, 960 / H


def fascia_uv(x, y):
    return (1024 + 3.42 * x) / W, (300 - 3.42 * y) / H


def bezel_uv(side, x, y):
    return ((512 if side < 0 else 1536) + 2.45 * x) / W, (572 - 2.45 * y) / H


def bc1(path, image):
    levels = []
    count = 0
    while True:
        out = io.BytesIO()
        image.save(out, format="DDS", pixel_format="DXT1")
        raw = out.getvalue()
        if not levels:
            header = bytearray(raw[:128])
        levels.append(raw[128:])
        count += 1
        if image.size == (1, 1):
            break
        image = image.resize(tuple(max(1, k // 2) for k in image.size), Image.Resampling.BOX)
    struct.pack_into("<I", header, 8, struct.unpack_from("<I", header, 8)[0] | 0x20000)
    struct.pack_into("<I", header, 28, count)
    struct.pack_into("<I", header, 108, 0x401008)
    path.write_bytes(header + b"".join(levels))


def dds(path, image):
    # Store independent linear channels; RGBA image resampling premultiplies alpha.
    planes = list(image.split())
    data = bytearray()
    levels = 0
    while True:
        data.extend(Image.merge("RGBA", planes).tobytes())
        levels += 1
        w, h = planes[0].size
        if w == h == 1:
            break
        planes = [p.resize((max(1, w//2), max(1, h//2)), Image.Resampling.BOX) for p in planes]
    w, h = image.size
    header = [124, 0x2100f, h, w, w*4, 0, levels, *([0]*11),
              32, 0x41, 0, 32, 0xff, 0xff00, 0xff0000, 0xff000000,
              0x401008, 0, 0, 0, 0]
    path.write_bytes(b"DDS " + struct.pack("<31I", *header) + data)


def write_textures(dest):
    rng = np.random.default_rng(133)
    ys, xs = np.mgrid[:H, :W]
    rgb = np.empty((H, W, 3), np.uint8)
    mats = np.empty((H, W, 4), np.uint8)

    def coat(mask, kind):
        tone, rough, metal = FINISHES[kind]
        grain = rng.normal(0, 2.4, (H, W)) + 1.1 * np.sin(ys * 1.19 + np.sin(xs * 0.019))
        rgb[mask] = np.uint8(np.clip(np.asarray(tone) + grain[mask, None], 0, 255))
        mats[mask, :2] = np.clip(128 + rng.normal(0, 2.8, (mask.sum(), 2)), 0, 255)
        mats[mask, 2] = np.clip(255 * rough + 1.4 * grain[mask], 0, 255)
        mats[mask, 3] = round(255 * metal)

    coat(ys < 320, "fascia")
    coat(ys >= 320, "bezel")
    for i, kind in enumerate(FINISHES):
        coat((ys > 886) & (xs >= 128 * i) & (xs < 128 * (i + 1)), kind)
    colour = Image.fromarray(rgb)
    d = ImageDraw.Draw(colour)

    def xy(uv, x, y):
        u, v = uv(x, y)
        return (round(u * W), round(v * H))

    def label(uv, x, y, text, mm, fill=(220, 227, 213), anchor="mm"):
        scale = abs(uv(1, 0)[0] - uv(0, 0)[0]) * W
        font = ImageFont.truetype(str(FONT), round(mm * scale))
        d.text(xy(uv, x, y), text, font=font, fill=fill, anchor=anchor, stroke_width=0)

    def rule(uv, x0, y0, x1, y1, tone=(145, 161, 161), width=2):
        d.line([xy(uv, x0, y0), xy(uv, x1, y1)], tone, width)

    f = fascia_uv
    label(f, -199, 40, "DELTA-GLIDER", 10, anchor="lm")
    label(f, -198, 31, "FLIGHT DECK", 5.1, (159, 183, 182), "lm")
    rule(f, -198, 15, -80, 15, (62, 75, 78), 3)
    for name, x, y in [("HUD MODE", 0, 68), ("RCS MODE", 65, 68), ("NAV MODE", 140, 54)]:
        label(f, x, y, name, 6.8)
    for x, text in [(-19, "ORB"), (0, "SRF"), (19, "DCK")]:
        label(f, x, 43.2, text, 3.4)
    label(f, -10, 13, "BRT", 4.8)
    label(f, 16.5, 19, "COL", 4.8)
    label(f, 46, 41, "OFF", 4.1)
    label(f, 65, 55, "ROT", 4.1)
    label(f, 85, 41, "LIN", 4.1)
    # Locator marks around the reaction-control selector.
    for dx, dy in [(-12, 8), (0, 15), (12, 8)]:
        rule(f, 65 + dx, 37 + dy, 65 + 1.15 * dx, 37 + 1.15 * dy, (216, 191, 132), 2)
    for x, y in [(-40, 65), (34, 69), (93, 66), (187, 45)]:
        rule(f, x, 8, x, y, (58, 73, 79), 3)
        rule(f, x + 0.6, 8, x + 0.6, y, (120, 134, 135), 1)
    for side in (-1, 1):

        def uv(x, y):
            return bezel_uv(side, x, y)

        label(uv, -59, -98, "MFD " + ("1" if side < 0 else "2"), 7.2)
        rule(uv, 38, -97, 73, -97, (154, 168, 168), 2)
        for x in (-95, 95):
            rule(uv, x - 4, 75, x + 4, 75, (166, 177, 171), 2)
    bc1(dest / "dg_flightdeck.dds", colour)
    surf = Image.fromarray(mats)
    # Independent packed channels, including metallicity in alpha.
    small = Image.merge("RGBA", [c.resize((512, 256), Image.Resampling.BOX) for c in surf.split()])
    dds(dest / "dg_flightdeck_surface.dds", small)
