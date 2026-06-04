from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_get_spatial_boundary():
    # 1. Create parent basin first
    basin_data = {
        "basin_id": "TEST-MARA-SB",
        "name": "Test Mara Basin",
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [34.5, -1.5],
                        [34.6, -1.5],
                        [34.6, -1.4],
                        [34.5, -1.4],
                        [34.5, -1.5],
                    ]
                ]
            ],
        },
    }
    client.post("/api/v1/basins", json=basin_data)

    # 2. Create spatial boundary (sub-county)
    sb_data = {
        "name": "Tarime District",
        "basin_id": "TEST-MARA-SB",
        "centroid_geom": {
            "type": "Point",
            "coordinates": [34.47, -1.24],
        },
    }
    response = client.post("/api/v1/reference/sub-counties", json=sb_data)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["name"] == "Tarime District"
    assert res_data["basin_id"] == "TEST-MARA-SB"
    assert res_data["centroid_geom"]["type"] == "Point"
    assert "id" in res_data

    # 3. Get all sub-counties
    response = client.get("/api/v1/reference/sub-counties")
    assert response.status_code == 200
    res_list = response.json()
    assert len(res_list) >= 1
    found = [x for x in res_list if x["name"] == "Tarime District"]
    assert len(found) == 1
    assert found[0]["centroid_geom"]["coordinates"] == [34.47, -1.24]
