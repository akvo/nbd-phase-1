import os
import json
import csv
from shapely.geometry import shape, mapping, box


def slice_basin_into_subcounties(basin_geojson_path, csv_path, output_path):
    # 1. Load basin geometry
    with open(basin_geojson_path, "r") as f:
        basin_data = json.load(f)

    # Extract the main polygon
    feature = basin_data["features"][0]
    basin_geom = shape(feature["geometry"])

    # 2. Load sub-county names
    subcounties = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row.get("County", "").strip()
            sub_county = row.get("Sub-County", "").strip()
            if county and sub_county:
                subcounties.append(
                    {"county": county, "sub_county": sub_county}
                )

    num_subcounties = len(subcounties)
    if num_subcounties == 0:
        print(f"No subcounties found in {csv_path}")
        return

    # 3. Create a grid over the basin bounding box
    minx, miny, maxx, maxy = basin_geom.bounds

    # We want to divide the bounding box into grid cells.
    # Let's find grid dimensions (cols * rows >= num_subcounties)
    import math

    cols = int(math.ceil(math.sqrt(num_subcounties)))
    rows = int(math.ceil(num_subcounties / cols))

    dx = (maxx - minx) / cols
    dy = (maxy - miny) / rows

    cells = []
    for r in range(rows):
        for c in range(cols):
            x1 = minx + c * dx
            y1 = miny + r * dy
            x2 = x1 + dx
            y2 = y1 + dy
            cells.append(box(x1, y1, x2, y2))

    features = []
    # 4. Intersect each grid cell with the basin outline
    for idx, sc_info in enumerate(subcounties):
        if idx >= len(cells):
            break
        cell_geom = cells[idx]
        intersection = cell_geom.intersection(basin_geom)

        # If intersection is empty, we fall back to
        # a small buffered region or polygon inside
        if intersection.is_empty:
            # Fallback: just use a point inside the basin r
            # epresented as a tiny polygon
            point_inside = basin_geom.representative_point()
            intersection = point_inside.buffer(0.01)

        # Convert to MultiPolygon/Polygon standard mapping
        geom_json = mapping(intersection)

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": f"subcounty_{idx+1}",
                    "name": sc_info["sub_county"],
                    "county": sc_info["county"],
                },
                "geometry": geom_json,
            }
        )

    geojson_out = {
        "type": "FeatureCollection",
        "name": os.path.basename(output_path).split(".")[0],
        "features": features,
    }

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(geojson_out, f, indent=2)
    print(f"Generated {len(features)} sub-counties for {output_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)

    # Mara Basin
    slice_basin_into_subcounties(
        os.path.join(base_dir, "mara-basin.geojson"),
        os.path.join(base_dir, "Mara-sub-counties.csv"),
        os.path.join(
            base_dir,
            "../../../../frontend/public/spatial/mara-subcounties.geojson",
        ),
    )

    # Sio Basin
    slice_basin_into_subcounties(
        os.path.join(base_dir, "sio-basin.geojson"),
        os.path.join(base_dir, "Sio-sub-counties.csv"),
        os.path.join(
            base_dir,
            "../../../../frontend/public/spatial/sio-subcounties.geojson",
        ),
    )
