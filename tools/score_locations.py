#!/usr/bin/env python3
"""
Knox Country Base Atlas — scoring.

Every location is scored from measurements, not vibes:

* Zombie pressure is MEASURED from the map's own zombie-population layer.
  Two aligned renders of the same view (layer off / layer on) are compared
  pixel by pixel. The layer paints a blue overlay whose strength tracks
  population density, so for each pixel we take the blue-shift
      d = (B_on - B_off) - (R_on - R_off)
  and combine coverage (share of pixels with d > 25) and mean intensity:
      pressure = round(0.6 * coverage_pct + 0.4 * min(100, mean_positive_d * 0.85))
  Safety = 100 - pressure.

* Loot, Water and Defense are editorial 0-10 scores read off the render and
  the item database (what the building holds, how far open water is, how
  much perimeter/floor structure the building already has). They live in
  data/locations_input.json so anyone can audit or challenge them.

* Overall = 0.30*Safety + 0.30*Loot*10 + 0.15*Water*10 + 0.25*Defense*10

Inputs : atlas/final/<slug>-clean.png, atlas/final/<slug>-zombie.png
         (aligned 1600x1200 captures of projectzomboidmap.net at step 16),
         data/locations_input.json
Outputs: data/locations.json, data/locations.csv
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FRAMES = os.path.expanduser(
    "~/workspace/goals/offpage-seo-work/files/atlas/final"
)
CROP_BOX = (200, 150, 1400, 1050)  # centre 1200x900 of the 1600x1200 frame


def measure_pressure(slug):
    clean = Image.open(os.path.join(FRAMES, f"{slug}-clean.png")).convert("RGB")
    zombie = Image.open(os.path.join(FRAMES, f"{slug}-zombie.png")).convert("RGB")
    c = np.asarray(clean.crop(CROP_BOX), dtype=np.int16)
    z = np.asarray(zombie.crop(CROP_BOX), dtype=np.int16)
    d = (z[:, :, 2] - c[:, :, 2]) - (z[:, :, 0] - c[:, :, 0])
    coverage = float((d > 25).mean() * 100)
    intensity = float(np.clip(d, 0, None).mean())
    pressure = round(0.6 * coverage + 0.4 * min(100.0, intensity * 0.85))
    return {
        "zombie_coverage_pct": round(coverage, 1),
        "zombie_intensity": round(intensity, 2),
        "zombie_pressure": pressure,
    }


def main():
    with open(os.path.join(REPO, "data", "locations_input.json")) as f:
        inputs = json.load(f)

    locations = []
    for entry in inputs:
        m = measure_pressure(entry["slug"])
        safety = 100 - m["zombie_pressure"]
        overall = round(
            0.30 * safety
            + 0.30 * entry["loot"] * 10
            + 0.15 * entry["water"] * 10
            + 0.25 * entry["defense"] * 10
        )
        locations.append(
            {
                **entry,
                **m,
                "safety": safety,
                "overall": overall,
                "map_url": (
                    f"https://projectzomboidmap.net/"
                    f"#{entry['x']}x{entry['y']}x16"
                ),
            }
        )

    locations.sort(key=lambda e: -e["overall"])
    for i, loc in enumerate(locations, 1):
        loc["rank"] = i

    with open(os.path.join(REPO, "data", "locations.json"), "w") as f:
        json.dump(locations, f, indent=1)

    cols = [
        "rank", "name", "town", "x", "y", "type", "zombie_pressure",
        "safety", "loot", "water", "defense", "overall", "map_url",
    ]
    with open(os.path.join(REPO, "data", "locations.csv"), "w") as f:
        f.write(",".join(cols) + "\n")
        for loc in locations:
            row = []
            for c in cols:
                v = str(loc[c])
                row.append(f'"{v}"' if "," in v else v)
            f.write(",".join(row) + "\n")

    for loc in locations:
        print(
            f"#{loc['rank']} {loc['name']}: overall {loc['overall']} "
            f"(pressure {loc['zombie_pressure']}, safety {loc['safety']}, "
            f"loot {loc['loot']}, water {loc['water']}, defense {loc['defense']})"
        )


if __name__ == "__main__":
    sys.exit(main())
