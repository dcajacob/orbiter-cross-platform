#!/usr/bin/env python3
# Licensed under the MIT License
"""Bake opt-in Orbiter surface tiles from public 2023 Florida NAIP orthophotos."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from io import BytesIO
import hashlib
import json
import math
import mmap
from pathlib import Path
import struct
import time
import zlib

import numpy as np
from PIL import Image
import requests

SERVICE = "https://imagery.geoplatform.gov/iipp/rest/services/NAIP/NAIP_plus/ImageServer"
SOURCE = "USDA NAIP, Florida 2023 (0.3 m source imagery), served by USDA Forest Service GTAC / GeoPlatform IIPP"
RUNWAY = (-80.682594, 28.596924)
PADS = ((-80.6043, 28.6084), (-80.6208, 28.6272))
DETAIL = 19
PIXELS = 1536
EARTH_RADIUS = 6371000
METRES_PER_DEGREE = math.radians(1) * EARTH_RADIUS


def tilespan(level):
    return 180.0 / (1 << (level - 4))


def bounds(key):
    level, row, column = key
    angle = tilespan(level)
    return column * angle - 180, 90 - (row + 1) * angle, (column + 1) * angle - 180, 90 - row * angle


def point(level, lon, lat):
    angle = tilespan(level)
    return level, int((90 - lat) / angle), int((lon + 180) / angle)


def feather(distance, inner, outer):
    weight = np.clip((outer - distance) / (outer - inner), 0, 1)
    return weight * weight * (3 - 2 * weight)


def coverage(key, pixels):
    west, south, east, north = bounds(key)
    u = (np.arange(pixels, dtype=np.float32) + .5) / pixels
    lon = west + (east - west) * u.astype(np.float64)[None, :]
    lat = north - (north - south) * u.astype(np.float64)[:, None]

    x = ((lon - RUNWAY[0]) * METRES_PER_DEGREE * math.cos(math.radians(RUNWAY[1]))).astype(np.float32)
    y = ((lat - RUNWAY[1]) * METRES_PER_DEGREE).astype(np.float32)
    heading = math.radians(330.01)
    cross = x * math.cos(heading) - y * math.sin(heading)
    along = x * math.sin(heading) + y * math.cos(heading)
    result = feather(np.hypot(cross, along - np.clip(along, -180, 5150)), 270, 485)
    for longitude, latitude in PADS:
        dx = ((lon - longitude) * METRES_PER_DEGREE * math.cos(math.radians(latitude))).astype(np.float32)
        dy = ((lat - latitude) * METRES_PER_DEGREE).astype(np.float32)
        result = np.maximum(result, feather(np.hypot(dx, dy), 430, 675))
    return result


class StockArchive:
    def __init__(self, path):
        with path.open("rb") as source:
            self.data = mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ)
        magic, header_size, _, self.offset, self.data_length, self.count, _, _, _, *self.roots =             struct.unpack_from("<4siiiq6i", self.data)
        if magic != b"TX\x01\x00" or header_size != 48 or self.offset != header_size + 32 * self.count:
            raise ValueError("Expected an Orbiter Surf.tree archive")

    def node(self, index):
        return struct.unpack_from("<qi5i", self.data, 48 + 32 * index)

    @lru_cache(maxsize=160)
    def bitmap(self, index):
        offset, length, *_ = self.node(index)
        end = self.node(index + 1)[0] if index + 1 < self.count else self.data_length
        dds = zlib.decompress(self.data[self.offset + offset:self.offset + end])
        if len(dds) != length:
            raise ValueError(f"Wrong DDS size for archive record {index}")
        with Image.open(BytesIO(dds)) as image:
            return image.convert("RGB")

    def tile(self, key, pixels):
        level, row, column = key
        index = self.roots[column >> (level - 4)]
        best = None
        for source_level in range(4, level + 1):
            if index < 0:
                break
            _, size, nw, ne, sw, se, _ = self.node(index)
            if size:
                best = (source_level, index)
            if source_level < level:
                bit = level - source_level - 1
                index = (nw, ne, sw, se)[2 * ((row >> bit) & 1) + ((column >> bit) & 1)]
        if best is None:
            raise ValueError(f"Stock archive has no coverage for tile {key}")
        source_level, record = best
        image = self.bitmap(record)
        stride = 1 << (level - source_level)
        x, y = column % stride, row % stride
        w, h = image.width / stride, image.height / stride
        return image.resize((pixels, pixels), Image.Resampling.BICUBIC,
                            box=(x * w, y * h, (x + 1) * w, (y + 1) * h))


def get(url, params=None):
    for attempt in range(4):
        try:
            response = requests.get(url, params=params, timeout=(8, 45))
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(1 + attempt)


def fetch(key):
    extent = bounds(key)
    description = get(SERVICE + "/exportImage", {
        "bbox": ",".join(map(str, extent)), "bboxSR": 4326, "imageSR": 4326,
        "size": f"{PIXELS},{PIXELS}", "format": "png24",
        "interpolation": "RSP_BilinearInterpolation", "bandIds": "0,1,2", "f": "json",
        "mosaicRule": json.dumps({"where": "state = 'FL' AND year = 2023 AND category = 1"}),
    }).json()
    returned = description.get("extent", {})
    if returned.get("spatialReference", {}).get("wkid") != 4326 or any(
        abs(returned.get(name, math.inf) - value) > 1e-9
        for name, value in zip(("xmin", "ymin", "xmax", "ymax"), extent)
    ):
        raise ValueError(f"NAIP extent mismatch for {key}: {description}")
    with Image.open(BytesIO(get(description["href"]).content)) as image:
        if image.size != (PIXELS, PIXELS):
            raise ValueError(f"NAIP size mismatch for {key}: {image.size}")
        return image.convert("RGB")


def save_dds(image, path):
    """Write a BC1 DDS including a full offline mip pyramid."""
    levels = []
    current = image
    header = None
    while True:
        encoded = BytesIO()
        current.save(encoded, format="DDS", pixel_format="DXT1")
        blob = encoded.getvalue()
        if header is None:
            header = bytearray(blob[:128])
        size = ((current.width + 3) // 4) * ((current.height + 3) // 4) * 8
        if len(blob) != 128 + size:
            raise ValueError("Pillow did not produce the expected BC1 payload")
        levels.append(blob[128:])
        if current.size == (1, 1):
            break
        current = current.resize((max(1, current.width // 2), max(1, current.height // 2)),
                                 Image.Resampling.BOX)
    struct.pack_into("<I", header, 8, struct.unpack_from("<I", header, 8)[0] | 0x20000)
    struct.pack_into("<I", header, 20, len(levels[0]))
    struct.pack_into("<I", header, 28, len(levels))
    struct.pack_into("<I", header, 108, 0x401008)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        output.write(header)
        output.writelines(levels)


def tile_file(directory, key):
    level, row, column = key
    return directory / str(level) / str(row) / f"{column}.dds"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path, help="Stock Earth/Archive/Surf.tree")
    parser.add_argument("output", type=Path, help="New offline texture directory")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory must be new")
    stock = StockArchive(args.stock)
    _, top, left = point(DETAIL, -80.725, 28.657)
    _, bottom, right = point(DETAIL, -80.586, 28.586)
    keys = [(DETAIL, row, column) for row in range(top, bottom + 1)
            for column in range(left, right + 1) if coverage((DETAIL, row, column), 32).max() > .01]
    print(f"Baking {len(keys)} level-{DETAIL} Kennedy tiles", flush=True)

    def bake(key):
        aerial = fetch(key)
        alpha = coverage(key, PIXELS)
        valid = np.asarray(aerial).max(axis=2) > 3
        alpha = Image.fromarray(np.rint(alpha * valid * 255).astype(np.uint8))
        output = Image.composite(aerial, stock.tile(key, PIXELS), alpha)
        save_dds(output, tile_file(args.output, key))
        print("/".join(map(str, key)), flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(bake, keys))

    baked = set(keys)
    parents = set(keys)
    for level, pixels in ((18, 1024), (17, 512), (16, 512)):
        parents = {(level, row // 2, column // 2) for _, row, column in parents}
        for key in sorted(parents):
            _, row, column = key
            output = stock.tile(key, pixels)
            for y in range(2):
                for x in range(2):
                    child = (level + 1, 2 * row + y, 2 * column + x)
                    if child in baked:
                        with Image.open(tile_file(args.output, child)) as detail:
                            output.paste(detail.convert("RGB").resize((pixels // 2, pixels // 2),
                                Image.Resampling.BOX), (x * pixels // 2, y * pixels // 2))
            save_dds(output, tile_file(args.output, key))
        baked.update(parents)

    manifest = {"source": SOURCE, "service": SERVICE, "projection": "EPSG:4326",
                "level_19_pixels": PIXELS, "tiles": {}}
    for key in sorted(baked):
        path = tile_file(args.output, key)
        manifest["tiles"][path.relative_to(args.output).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (args.output / "imagery.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
