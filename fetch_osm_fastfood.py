from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from math import ceil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "cleaned"
ENDPOINTS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# South, west, north, east. Territory boxes overlap slightly at borders;
# OSM element type/id de-duplication removes duplicate returned outlets.
STATE_BOXES = {
    "Western Australia": (-36.0, 112.0, -13.0, 129.2),
    "Northern Territory": (-26.1, 129.0, -10.0, 138.2),
    "South Australia": (-38.5, 129.0, -25.8, 141.2),
    "Queensland": (-29.2, 137.8, -9.0, 154.2),
    "New South Wales": (-38.1, 140.8, -28.0, 154.0),
    "Victoria": (-39.4, 140.8, -33.7, 150.2),
    "Tasmania": (-44.0, 143.4, -39.3, 149.0),
    "Australian Capital Territory": (-35.95, 148.7, -35.05, 149.5),
}


def query_for_bbox(bbox):
    south, west, north, east = bbox
    return f"""[out:json][timeout:180][bbox:{south},{west},{north},{east}];
(
  node["amenity"="fast_food"];
  way["amenity"="fast_food"];
  relation["amenity"="fast_food"];
);
out center tags;"""


def tiles_for_bbox(bbox, step=2.0):
    south, west, north, east = bbox
    lat_tiles = max(1, ceil((north - south) / step))
    lon_tiles = max(1, ceil((east - west) / step))
    for lat_index in range(lat_tiles):
        tile_south = south + lat_index * step
        tile_north = min(north, tile_south + step)
        for lon_index in range(lon_tiles):
            tile_west = west + lon_index * step
            tile_east = min(east, tile_west + step)
            yield (tile_south, tile_west, tile_north, tile_east)


def post_query(query):
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error = None
    for endpoint in ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, data=body, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urllib.request.urlopen(req, timeout=240) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            last_error = error
    raise RuntimeError(f"All Overpass endpoints failed: {last_error}")


def element_coordinates(element):
    if element["type"] == "node":
        return element.get("lat"), element.get("lon")
    center = element.get("center", {})
    return center.get("lat"), center.get("lon")


def clean_tag(tags, key):
    return str(tags.get(key, "")).strip()


def build_locations():
    rows = {}
    raw_batches = {}
    for state, bbox in STATE_BOXES.items():
        raw_batches[state] = []
        for tile_number, tile in enumerate(tiles_for_bbox(bbox), start=1):
            try:
                payload = post_query(query_for_bbox(tile))
            except Exception as error:
                print(f"{state}: tile {tile_number} failed, skipping: {error}")
                continue
            raw_batches[state].append({"tile": tile, "payload": payload})
            print(f"{state}: tile {tile_number}, {len(payload.get('elements', []))} elements")
            for element in payload.get("elements", []):
                lat, lon = element_coordinates(element)
                if lat is None or lon is None:
                    continue
                tags = element.get("tags", {})
                key = f"{element['type']}/{element['id']}"
                rows[key] = {
                    "name": clean_tag(tags, "name"),
                    "brand": clean_tag(tags, "brand"),
                    "cuisine": clean_tag(tags, "cuisine"),
                    "lat": round(float(lat), 6),
                    "lon": round(float(lon), 6),
                    "state": state,
                    "source": "OpenStreetMap amenity=fast_food via Overpass",
                }
            time.sleep(0.4)

    RAW.mkdir(parents=True, exist_ok=True)
    CLEAN.mkdir(parents=True, exist_ok=True)
    (RAW / "osm_fastfood_batches.json").write_text(json.dumps(raw_batches), encoding="utf-8")
    output = CLEAN / "fastfood_locations.csv"
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "brand", "cuisine", "lat", "lon", "state", "source"])
        writer.writeheader()
        writer.writerows(rows.values())
    print(f"Wrote {len(rows):,} OSM fast-food locations to {output}")


if __name__ == "__main__":
    build_locations()
