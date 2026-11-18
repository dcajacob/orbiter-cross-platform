"""Compare two native Linux flight captures made with one Launchpad setting changed.

Pass the off (or lower-detail) evidence directory first. Use a fixed step, capture
time and UI clock for both flights. The KSC tour exercises daytime terrain. A
date four days later puts clouds over the runway at the same playback time.
The stock City lights at night scenario exercises the emissive Earth mask.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np


def read_json(directory, name):
    return json.loads((directory / name).read_text())


def earth_draws(directory):
    with (directory / "planet-tiles.csv").open() as source:
        return next(int(row["textured_draw_calls"]) for row in csv.DictReader(source)
                    if row["object"] == "Earth")


def compare(setting, before, after):
    low, high = [read_json(d, "native-render-settings.json") for d in (before, after)]
    if low.keys() != high.keys() or {k for k in low if low[k] != high[k]} != {setting} or low[setting] >= high[setting]:
        raise ValueError(f"Expected only {setting} to increase")
    if setting == "cloud_shadows" and not high["clouds"]:
        raise ValueError("Cloud shadows require clouds")
    for name in ("camera.csv", "scene.csv", "flight-state.csv"):
        if (before / name).read_bytes() != (after / name).read_bytes():
            raise ValueError(f"Flight or camera changed between captures: {name}")
    summaries = [read_json(d, "scene-summary.json") for d in (before, after)]
    for key in ("width", "height", "simulation_seconds", "frames"):
        if summaries[0][key] != summaries[1][key]:
            raise ValueError(f"Capture mismatch: {key}")
    height, width = (summaries[0][key] for key in ("height", "width"))
    frames = [np.fromfile(d / "scene.rgba", np.uint8).reshape(height, width, 4)[::-1, :, :3]
              for d in (before, after)]
    delta = frames[1].astype(np.int16) - frames[0]
    # Omit screen edges and the replay caption. Compare sky for clouds, terrain
    # for shadows/detail, and the Earth-facing camera view for city lights.
    region = delta[:height // 5] if setting == "clouds" else delta[height // 3:height * 4 // 5]
    region = region[:, width // 3:width * 9 // 10]
    if setting == "cloud_shadows":
        signal = -region.min(axis=2)
        if region.max() > 1:
            raise ValueError("Enabling shadows brightened the terrain")
    elif setting == "night_lights":
        signal = region.max(axis=2)
        if region.min() < -1:
            raise ValueError("Enabling city lights darkened the night view")
    else:
        signal = np.abs(region).max(axis=2)
    changed = int((signal >= 3).sum())
    if changed < 50:
        raise ValueError(f"Too little visible change in the comparison region: {changed} pixels")
    result = {"setting": setting, "from": low[setting], "to": high[setting],
              "region_pixels_changed_by_at_least_3": changed,
              "whole_frame_changed_pixels": int(np.any(delta, axis=2).sum())}
    if setting == "planet_max_level":
        draws = [earth_draws(d) for d in (before, after)]
        if draws[1] <= draws[0]:
            raise ValueError(f"Raising the cap did not increase Earth tile draws: {draws}")
        result["earth_tile_draws"] = draws
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setting", choices=["clouds", "cloud_shadows", "night_lights", "planet_max_level"])
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.setting, args.before, args.after), indent=2))
