import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.spatial import BoundaryLevel
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def test_boundary_level_enum():
    assert BoundaryLevel.WARD == 4
    assert BoundaryLevel.WARD.value == 4
    assert BoundaryLevel.WARD.name == "WARD"


@pytest.fixture
def auth_headers(db_session: Session):
    admin = User(email="admin_sb_test@nbd.org", role="Admin", is_active=True)
    db_session.add(admin)
    db_session.commit()
    token = jwt.encode(
        {"email": "admin_sb_test@nbd.org"},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_spatial_boundary(auth_headers):
    # 1. Create parent basin first
    basin_data = {
        "code": "TEST-MARA-SB",
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
    res_basin = client.post(
        "/api/v1/basins", json=basin_data, headers=auth_headers
    )
    assert res_basin.status_code == 201
    basin_uuid = res_basin.json()["id"]

    # 2. Create spatial boundary Region (level=1)
    sb_region_data = {
        "name": "Mara Region Test",
        "level": 1,
        "parent_id": None,
        "basin_id": basin_uuid,
        "centroid_geom": {
            "type": "Point",
            "coordinates": [34.5, -1.5],
        },
    }
    response_reg = client.post(
        "/api/v1/reference/sub-counties",
        json=sb_region_data,
        headers=auth_headers,
    )
    assert response_reg.status_code == 201
    res_reg_data = response_reg.json()
    assert res_reg_data["name"] == "Mara Region Test"
    assert res_reg_data["level"] == 1
    assert res_reg_data["parent_id"] is None
    region_uuid = res_reg_data["id"]

    # 3. Create spatial boundary District (level=2)
    sb_district_data = {
        "name": "Tarime District Test",
        "level": 2,
        "parent_id": region_uuid,
        "basin_id": basin_uuid,
        "centroid_geom": {
            "type": "Point",
            "coordinates": [34.47, -1.24],
        },
    }
    response_dist = client.post(
        "/api/v1/reference/sub-counties",
        json=sb_district_data,
        headers=auth_headers,
    )
    assert response_dist.status_code == 201
    res_dist_data = response_dist.json()
    assert res_dist_data["name"] == "Tarime District Test"
    assert res_dist_data["level"] == 2
    assert res_dist_data["parent_id"] == region_uuid

    # 4. Get all sub-counties
    response = client.get(
        "/api/v1/reference/sub-counties", headers=auth_headers
    )
    assert response.status_code == 200
    res_list = response.json()
    assert len(res_list) >= 2
    found = [x for x in res_list if x["name"] == "Tarime District Test"]
    assert len(found) == 1
    assert found[0]["centroid_geom"]["coordinates"] == [34.47, -1.24]
    assert found[0]["level"] == 2
    assert found[0]["parent_id"] == region_uuid


def test_create_spatial_boundary_null_centroid(auth_headers):
    # 1. Create parent basin first
    basin_data = {
        "code": "TEST-MARA-SB-NULL",
        "name": "Test Mara Basin Null",
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
    res_basin = client.post(
        "/api/v1/basins", json=basin_data, headers=auth_headers
    )
    assert res_basin.status_code == 201
    basin_uuid = res_basin.json()["id"]

    # 2. Create spatial boundary Region with null centroid_geom
    sb_region_data = {
        "name": "Mara Null Centroid Test",
        "level": 1,
        "parent_id": None,
        "basin_id": basin_uuid,
        "centroid_geom": None,
    }
    response_reg = client.post(
        "/api/v1/reference/sub-counties",
        json=sb_region_data,
        headers=auth_headers,
    )
    print(response_reg.json(), "---AAA")
    assert response_reg.status_code == 201
    res_reg_data = response_reg.json()
    assert res_reg_data["name"] == "Mara Null Centroid Test"
    assert res_reg_data["centroid_geom"] is None


def test_list_wards_endpoint(auth_headers):
    # 1. Create parent basin
    basin_data = {
        "code": "TEST-MARA-WARD-EP",
        "name": "Test Ward Endpoint Basin",
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
    res_basin = client.post(
        "/api/v1/basins", json=basin_data, headers=auth_headers
    )
    assert res_basin.status_code == 201
    basin_uuid = res_basin.json()["id"]

    # 2. Create Sub-County (L3)
    sc_data = {
        "name": "Sub-County Ward Test",
        "level": 3,
        "parent_id": None,
        "basin_id": basin_uuid,
        "centroid_geom": None,
    }
    res_sc = client.post(
        "/api/v1/reference/sub-counties", json=sc_data, headers=auth_headers
    )
    assert res_sc.status_code == 201
    sc_uuid = res_sc.json()["id"]

    # 3. Create Ward (L4) under Sub-County
    ward_data = {
        "name": "Ward Endpoint Test",
        "level": 4,
        "parent_id": sc_uuid,
        "basin_id": basin_uuid,
        "centroid_geom": None,
    }
    res_ward = client.post(
        "/api/v1/reference/sub-counties", json=ward_data, headers=auth_headers
    )
    assert res_ward.status_code == 201

    # 4. GET /reference/wards/{sc_uuid}
    response = client.get(
        f"/api/v1/reference/wards/{sc_uuid}", headers=auth_headers
    )
    assert response.status_code == 200
    wards_list = response.json()
    assert len(wards_list) == 1
    assert wards_list[0]["name"] == "Ward Endpoint Test"
    assert wards_list[0]["level"] == 4

    # 5. Invalid UUID returns empty list
    invalid_res = client.get(
        "/api/v1/reference/wards/not-a-uuid", headers=auth_headers
    )
    assert invalid_res.status_code == 200
    assert invalid_res.json() == []
