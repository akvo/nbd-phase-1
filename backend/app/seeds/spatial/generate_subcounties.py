import os
import json


def load_proper_subcounties(geojson_input_path, output_path):
    with open(geojson_input_path, "r") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        sub_county_name = props.get("Sub-County", "")
        county_name = props.get("County", "")
        # Add keys required by frontend
        props["name"] = sub_county_name
        props["county"] = county_name

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(
        f"Processed and copied proper subcounties from {geojson_input_path} to {output_path}"  # noqa
    )


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)

    # Mara Subcounties
    load_proper_subcounties(
        os.path.join(base_dir, "mara-kenya-subcounties.geojson"),
        os.path.join(
            base_dir,
            "output/mara-subcounties.geojson",
        ),
    )

    # Sio Subcounties
    load_proper_subcounties(
        os.path.join(base_dir, "sio-kenya-subcounties.geojson"),
        os.path.join(
            base_dir,
            "output/sio-subcounties.geojson",
        ),
    )
