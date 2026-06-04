from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_get_basin():
    # Create
    basin_data = {
        "basin_id": "TEST-MARA",
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
    response = client.post("/api/v1/basins", json=basin_data)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["basin_id"] == "TEST-MARA"
    assert res_data["name"] == "Test Mara Basin"
    assert res_data["geom"]["type"] == "MultiPolygon"

    # Get
    response = client.get("/api/v1/basins/TEST-MARA")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Mara Basin"


def test_create_basin_invalid_geom():
    basin_data = {
        "basin_id": "TEST-INVALID",
        "name": "Invalid Basin",
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [34.5, -1.5],
                        [
                            34.6,
                            -1.5,
                        ],  # Only 2 points, invalid for a polygon shell
                    ]
                ]
            ],
        },
    }
    response = client.post("/api/v1/basins", json=basin_data)
    assert response.status_code == 422


def test_create_wetland_success():
    # 1. Create parent basin first
    basin_data = {
        "basin_id": "TEST-BASIN-2",
        "name": "Test Basin 2",
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [34.0, -1.0],
                        [35.0, -1.0],
                        [35.0, 0.0],
                        [34.0, 0.0],
                        [34.0, -1.0],
                    ]
                ]
            ],
        },
    }
    client.post("/api/v1/basins", json=basin_data)

    # 2. Create Wetland
    wetland_data = {
        "wetland_id": "TEST-WETLAND-1",
        "basin_id": "TEST-BASIN-2",
        "name": "Test Wetland 1",
        "geom": {
            "type": "Polygon",
            "coordinates": [
                [
                    [34.1, -0.9],
                    [34.9, -0.9],
                    [34.9, -0.1],
                    [34.1, -0.1],
                    [34.1, -0.9],
                ]
            ],
        },
    }
    response = client.post("/api/v1/wetlands", json=wetland_data)
    assert response.status_code == 201
    assert response.json()["wetland_id"] == "TEST-WETLAND-1"


def test_create_wetland_missing_basin():
    wetland_data = {
        "wetland_id": "TEST-WETLAND-ERR",
        "basin_id": "NON-EXISTENT-BASIN",
        "name": "Test Wetland Err",
        "geom": {
            "type": "Polygon",
            "coordinates": [
                [
                    [34.1, -0.9],
                    [34.9, -0.9],
                    [34.9, -0.1],
                    [34.1, -0.1],
                    [34.1, -0.9],
                ]
            ],
        },
    }
    response = client.post("/api/v1/wetlands", json=wetland_data)
    assert response.status_code == 400
    assert "Parent Basin" in response.json()["detail"]


def test_create_site_success_and_fail():
    # 1. Create parent basin & wetland
    basin_data = {
        "basin_id": "TEST-BASIN-3",
        "name": "Test Basin 3",
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [34.0, -1.0],
                        [35.0, -1.0],
                        [35.0, 0.0],
                        [34.0, 0.0],
                        [34.0, -1.0],
                    ]
                ]
            ],
        },
    }
    client.post("/api/v1/basins", json=basin_data)

    wetland_data = {
        "wetland_id": "TEST-WETLAND-3",
        "basin_id": "TEST-BASIN-3",
        "name": "Test Wetland 3",
        "geom": {
            "type": "Polygon",
            "coordinates": [
                [
                    [34.1, -0.9],
                    [34.9, -0.9],
                    [34.9, -0.1],
                    [34.1, -0.1],
                    [34.1, -0.9],
                ]
            ],
        },
    }
    client.post("/api/v1/wetlands", json=wetland_data)

    # 2. Create Site (Success)
    site_data = {
        "site_id": "TEST-SITE-1",
        "wetland_id": "TEST-WETLAND-3",
        "name": "Test Site 1",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    response = client.post("/api/v1/sites", json=site_data)
    assert response.status_code == 201
    assert response.json()["site_id"] == "TEST-SITE-1"

    # 3. Create Site with invalid parent wetland (Failure)
    site_data_invalid = {
        "site_id": "TEST-SITE-2",
        "wetland_id": "NON-EXISTENT-WETLAND",
        "name": "Test Site 2",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    response = client.post("/api/v1/sites", json=site_data_invalid)
    assert response.status_code == 400
    assert "Parent Wetland" in response.json()["detail"]


def test_spatial_duplicates_and_404s():
    # 1. Duplicate Basin Check
    basin_data = {
        "basin_id": "DUP-BASIN",
        "name": "Basin",
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [34.0, -1.0],
                        [35.0, -1.0],
                        [35.0, 0.0],
                        [34.0, 0.0],
                        [34.0, -1.0],
                    ]
                ]
            ],
        },
    }
    res1 = client.post("/api/v1/basins", json=basin_data)
    assert res1.status_code == 201
    res2 = client.post("/api/v1/basins", json=basin_data)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]

    # 404 Basin
    res_404 = client.get("/api/v1/basins/NON-EXISTENT")
    assert res_404.status_code == 404

    # 2. Duplicate Wetland Check
    wetland_data = {
        "wetland_id": "DUP-WETLAND",
        "basin_id": "DUP-BASIN",
        "name": "Wetland",
        "geom": {
            "type": "Polygon",
            "coordinates": [
                [
                    [34.1, -0.9],
                    [34.9, -0.9],
                    [34.9, -0.1],
                    [34.1, -0.1],
                    [34.1, -0.9],
                ]
            ],
        },
    }
    res_w1 = client.post("/api/v1/wetlands", json=wetland_data)
    assert res_w1.status_code == 201
    res_w2 = client.post("/api/v1/wetlands", json=wetland_data)
    assert res_w2.status_code == 400
    assert "already exists" in res_w2.json()["detail"]

    # 404 Wetland
    res_w_404 = client.get("/api/v1/wetlands/NON-EXISTENT")
    assert res_w_404.status_code == 404

    # 3. Duplicate Site Check
    site_data = {
        "site_id": "DUP-SITE",
        "wetland_id": "DUP-WETLAND",
        "name": "Site",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    res_s1 = client.post("/api/v1/sites", json=site_data)
    assert res_s1.status_code == 201
    res_s2 = client.post("/api/v1/sites", json=site_data)
    assert res_s2.status_code == 400
    assert "already exists" in res_s2.json()["detail"]

    # 404 Site
    res_s_404 = client.get("/api/v1/sites/NON-EXISTENT")
    assert res_s_404.status_code == 404


@patch("app.routers.spatial_router.from_shape")
def test_router_exceptions(mock_from_shape):
    mock_from_shape.side_effect = Exception("DB error mock")

    # Basin Create exception
    basin_data = {
        "basin_id": "EXC-BASIN",
        "name": "Basin",
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [34.0, -1.0],
                        [35.0, -1.0],
                        [35.0, 0.0],
                        [34.0, 0.0],
                        [34.0, -1.0],
                    ]
                ]
            ],
        },
    }
    res = client.post("/api/v1/basins", json=basin_data)
    assert res.status_code == 400

    # Create dummy parent for wetland exception test
    mock_from_shape.side_effect = None
    client.post("/api/v1/basins", json=basin_data)

    # Wetland Create exception
    mock_from_shape.side_effect = Exception("DB error mock")
    wetland_data = {
        "wetland_id": "EXC-WETLAND",
        "basin_id": "EXC-BASIN",
        "name": "Wetland",
        "geom": {
            "type": "Polygon",
            "coordinates": [
                [
                    [34.1, -0.9],
                    [34.9, -0.9],
                    [34.9, -0.1],
                    [34.1, -0.1],
                    [34.1, -0.9],
                ]
            ],
        },
    }
    res = client.post("/api/v1/wetlands", json=wetland_data)
    assert res.status_code == 400

    # Create dummy parent for site exception test
    mock_from_shape.side_effect = None
    client.post("/api/v1/wetlands", json=wetland_data)

    # Site Create exception
    mock_from_shape.side_effect = Exception("DB error mock")
    site_data = {
        "site_id": "EXC-SITE",
        "wetland_id": "EXC-WETLAND",
        "name": "Site",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    res = client.post("/api/v1/sites", json=site_data)
    assert res.status_code == 400
