import uuid
import jwt
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.config.auth import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def create_admin_token(email: str = "admin_spatial@nbd.org") -> str:
    return jwt.encode({"email": email}, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def setup_admin_user(db_session: Session):
    """Create an admin user for tests that require authentication."""
    admin = User(
        email="admin_spatial@nbd.org",
        role="Admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.flush()  # Use flush instead of commit for test isolation
    return admin


def test_create_and_get_basin(setup_admin_user):
    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Create
    basin_data = {
        "code": "TEST-MARA",
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
    response = client.post("/api/v1/basins", json=basin_data, headers=headers)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["code"] == "TEST-MARA"
    assert res_data["name"] == "Test Mara Basin"
    assert res_data["geom"]["type"] == "MultiPolygon"
    assert "id" in res_data

    # Get by slug
    response = client.get("/api/v1/basins/TEST-MARA")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Mara Basin"

    # Get by UUID
    response = client.get(f"/api/v1/basins/{res_data['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Mara Basin"

    # List basins
    response = client.get("/api/v1/basins")
    assert response.status_code == 200
    basins_list = response.json()
    assert isinstance(basins_list, list)
    assert len(basins_list) >= 1
    assert any(b["code"] == "TEST-MARA" for b in basins_list)


def test_create_basin_invalid_geom(setup_admin_user):
    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}
    basin_data = {
        "code": "TEST-INVALID",
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
    response = client.post("/api/v1/basins", json=basin_data, headers=headers)
    assert response.status_code == 422


def test_create_wetland_success(setup_admin_user):
    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}
    # 1. Create parent basin first
    basin_data = {
        "code": "TEST-BASIN-2",
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
    res_basin = client.post("/api/v1/basins", json=basin_data, headers=headers)
    assert res_basin.status_code == 201
    basin_uuid = res_basin.json()["id"]

    # 2. Create Wetland
    wetland_data = {
        "code": "TEST-WETLAND-1",
        "basin_id": basin_uuid,
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
    response = client.post(
        "/api/v1/wetlands", json=wetland_data, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["code"] == "TEST-WETLAND-1"
    assert response.json()["basin_id"] == basin_uuid


def test_create_wetland_missing_basin(setup_admin_user):
    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}
    fake_uuid = str(uuid.uuid4())
    wetland_data = {
        "code": "TEST-WETLAND-ERR",
        "basin_id": fake_uuid,
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
    response = client.post(
        "/api/v1/wetlands", json=wetland_data, headers=headers
    )
    assert response.status_code == 400
    assert "Parent Basin" in response.json()["detail"]


def test_create_site_success_and_fail(setup_admin_user):
    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create parent basin & wetland
    basin_data = {
        "code": "TEST-BASIN-3",
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
    res_basin = client.post("/api/v1/basins", json=basin_data, headers=headers)
    basin_uuid = res_basin.json()["id"]

    wetland_data = {
        "code": "TEST-WETLAND-3",
        "basin_id": basin_uuid,
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
    res_wetland = client.post(
        "/api/v1/wetlands", json=wetland_data, headers=headers
    )
    wetland_uuid = res_wetland.json()["id"]

    # 2. Create Site (Success) - requires Admin auth
    site_data = {
        "code": "TEST-SITE-1",
        "wetland_id": wetland_uuid,
        "name": "Test Site 1",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    response = client.post("/api/v1/sites", json=site_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["code"] == "TEST-SITE-1"
    assert response.json()["wetland_id"] == wetland_uuid

    # 3. Create Site with invalid parent wetland (Failure)
    fake_uuid = str(uuid.uuid4())
    site_data_invalid = {
        "code": "TEST-SITE-2",
        "wetland_id": fake_uuid,
        "name": "Test Site 2",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    response = client.post(
        "/api/v1/sites", json=site_data_invalid, headers=headers
    )
    assert response.status_code == 400
    assert "Parent Wetland" in response.json()["detail"]


def test_spatial_duplicates_and_404s(setup_admin_user):
    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Duplicate Basin Check
    basin_data = {
        "code": "DUP-BASIN",
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
    res1 = client.post("/api/v1/basins", json=basin_data, headers=headers)
    assert res1.status_code == 201
    basin_uuid = res1.json()["id"]
    res2 = client.post("/api/v1/basins", json=basin_data, headers=headers)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]

    # 404 Basin
    res_404 = client.get(f"/api/v1/basins/{uuid.uuid4()}")
    assert res_404.status_code == 404

    # 2. Duplicate Wetland Check
    wetland_data = {
        "code": "DUP-WETLAND",
        "basin_id": basin_uuid,
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
    res_w1 = client.post(
        "/api/v1/wetlands", json=wetland_data, headers=headers
    )
    assert res_w1.status_code == 201
    wetland_uuid = res_w1.json()["id"]
    res_w2 = client.post(
        "/api/v1/wetlands", json=wetland_data, headers=headers
    )
    assert res_w2.status_code == 400
    assert "already exists" in res_w2.json()["detail"]

    # 404 Wetland
    res_w_404 = client.get(f"/api/v1/wetlands/{uuid.uuid4()}")
    assert res_w_404.status_code == 404

    # 3. Duplicate Site Check - requires Admin auth
    site_data = {
        "code": "DUP-SITE",
        "wetland_id": wetland_uuid,
        "name": "Site",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    res_s1 = client.post("/api/v1/sites", json=site_data, headers=headers)
    assert res_s1.status_code == 201
    res_s2 = client.post("/api/v1/sites", json=site_data, headers=headers)
    assert res_s2.status_code == 400
    assert "already exists" in res_s2.json()["detail"]

    # 404 Site
    res_s_404 = client.get(f"/api/v1/sites/{uuid.uuid4()}")
    assert res_s_404.status_code == 404


@patch("app.routers.spatial_router.from_shape")
def test_router_exceptions(mock_from_shape, db_session: Session):
    from geoalchemy2.shape import from_shape as real_from_shape

    def ensure_admin():
        admin_user = (
            db_session.query(User)
            .filter(User.email == "admin_spatial@nbd.org")
            .first()
        )
        if not admin_user:
            admin_user = User(
                email="admin_spatial@nbd.org",
                role="Admin",
                is_active=True,
            )
            db_session.add(admin_user)
            db_session.commit()

    ensure_admin()

    admin_token = create_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    mock_from_shape.side_effect = Exception("DB error mock")

    # Basin Create exception
    basin_data = {
        "code": "EXC-BASIN",
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
    res = client.post("/api/v1/basins", json=basin_data, headers=headers)
    assert res.status_code == 400

    # Restore admin user lost during rollback
    ensure_admin()

    # Create dummy parent for wetland exception test
    mock_from_shape.side_effect = real_from_shape
    res_b = client.post("/api/v1/basins", json=basin_data, headers=headers)
    basin_uuid = res_b.json()["id"]

    # Wetland Create exception
    mock_from_shape.side_effect = Exception("DB error mock")
    wetland_data = {
        "code": "EXC-WETLAND",
        "basin_id": basin_uuid,
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
    res = client.post("/api/v1/wetlands", json=wetland_data, headers=headers)
    assert res.status_code == 400

    # Restore admin user lost during rollback
    ensure_admin()

    # Create dummy parent for site exception test
    mock_from_shape.side_effect = real_from_shape
    res_w = client.post("/api/v1/wetlands", json=wetland_data, headers=headers)
    wetland_uuid = res_w.json()["id"]

    # Site Create exception - requires Admin auth
    mock_from_shape.side_effect = Exception("DB error mock")
    site_data = {
        "code": "EXC-SITE",
        "wetland_id": wetland_uuid,
        "name": "Site",
        "geom": {"type": "Point", "coordinates": [34.5, -0.5]},
    }
    res = client.post("/api/v1/sites", json=site_data, headers=headers)
    assert res.status_code == 400


def test_spatial_not_found_routes():
    fake_uuid = str(uuid.uuid4())
    # Non-existent basin
    res = client.get(f"/api/v1/basins/{fake_uuid}")
    assert res.status_code == 404

    # Non-existent wetland
    res = client.get(f"/api/v1/wetlands/{fake_uuid}")
    assert res.status_code == 404

    # Non-existent site
    res = client.get(f"/api/v1/sites/{fake_uuid}")
    assert res.status_code == 404


def test_enrich_site_status_abnormal_metrics(db_session):
    from decimal import Decimal
    from app.models.spatial import Basin, Wetland, Site
    from app.models.health_score import HealthScore
    from app.models.sampling_record import SamplingRecord
    from app.routers.spatial_router import compute_site_status

    b_geom = "SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))"
    basin = Basin(name="Abnormal Basin", code="AB-BASIN", geom=b_geom)
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        name="Abnormal Wetland",
        code="AB-WETLAND",
        basin_id=basin.id,
        geom=b_geom,
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        name="Abnormal Site",
        code="AB-SITE",
        wetland_id=wetland.id,
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    score = HealthScore(
        site_id=site.id,
        wqi_score=Decimal("0.20"),
        composite_score=Decimal("0.30"),
        ik_signal_value=Decimal("0.50"),
        adjusted_score=Decimal("0.25"),
        health_class="D",
    )
    db_session.add(score)

    from datetime import datetime

    sampling = SamplingRecord(
        site_id=site.id,
        ph_value=Decimal("5.5"),  # Abnormal < 6.5
        temp_value=Decimal("35.0"),  # Abnormal > 30
        do_value=Decimal("3.0"),  # Low < 5.0
        water_level="HIGH",  # Flood Risk
        invasive_macrophytes=Decimal("50.0"),
        sampled_at=datetime.utcnow(),
    )
    db_session.add(sampling)
    db_session.commit()

    compute_site_status(db_session, site)

    status = site.status
    assert status["metrics"]["ph"]["status"] == "Abnormal"
    assert status["metrics"]["temperature"]["status"] == "Abnormal"
    assert status["metrics"]["dissolved_oxygen"]["status"] == "Low"
    assert status["metrics"]["water_level"]["status"] == "Flood Risk"
    assert status["score_breakdown"]["catchment_hydrological"]["score"] == 0.60


def test_reference_cascade_endpoints(db_session):
    # Test list_all_sub_counties and filter by parent_id
    res = client.get("/api/v1/reference/sub-counties")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    res_root = client.get("/api/v1/reference/sub-counties/0")
    assert res_root.status_code == 200
    assert isinstance(res_root.json(), list)

    res_invalid = client.get("/api/v1/reference/sub-counties/invalid-id")
    assert res_invalid.status_code == 200
    assert res_invalid.json() == []

    # Test list_wards with invalid UUID
    res_wards_invalid = client.get("/api/v1/reference/wards/invalid-id")
    assert res_wards_invalid.status_code == 200
    assert res_wards_invalid.json() == []

    # Test list_all_reference_wetlands & list_reference_wetlands
    res_wetlands_all = client.get("/api/v1/reference/wetlands")
    assert res_wetlands_all.status_code == 200
    assert isinstance(res_wetlands_all.json(), list)

    res_wetlands_invalid = client.get("/api/v1/reference/wetlands/invalid-id")
    assert res_wetlands_invalid.status_code == 200
    assert res_wetlands_invalid.json() == []

    # Test list_all_reference_sites & list_reference_sites
    res_sites_all = client.get("/api/v1/reference/sites")
    assert res_sites_all.status_code == 200
    assert isinstance(res_sites_all.json(), list)

    res_sites_invalid = client.get("/api/v1/reference/sites/invalid-id")
    assert res_sites_invalid.status_code == 200
    assert res_sites_invalid.json() == []

    # Test cascade options
    res_cascade = client.get("/api/v1/reference/cascade-options")
    assert res_cascade.status_code == 200
    assert len(res_cascade.json()) == 3
