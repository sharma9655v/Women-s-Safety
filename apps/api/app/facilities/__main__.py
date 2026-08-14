from __future__ import annotations

import argparse
import json

from app.facilities.fetcher import FacilityFetcher, validate_bbox


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = [float(p) for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be min_lon,min_lat,max_lon,max_lat")
    return (parts[0], parts[1], parts[2], parts[3])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch safety-relevant facilities from Overpass into GeoJSON."
    )
    parser.add_argument(
        "--bbox",
        required=True,
        type=parse_bbox,
        help="min_lon,min_lat,max_lon,max_lat (e.g. 76.9,28.4,77.4,28.9)",
    )
    parser.add_argument("--out", default="facilities.geojson", help="output path")
    parser.add_argument("--base-url", default="https://overpass-api.de/api/interpreter")
    args = parser.parse_args()

    min_lon, min_lat, max_lon, max_lat = args.bbox
    validate_bbox(min_lon, min_lat, max_lon, max_lat)

    fetcher = FacilityFetcher(base_url=args.base_url)
    try:
        collection = fetcher.fetch(min_lon, min_lat, max_lon, max_lat)
    finally:
        fetcher.close()

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, ensure_ascii=False)
    print(f"wrote {len(collection['features'])} facilities to {args.out}")


if __name__ == "__main__":
    main()
