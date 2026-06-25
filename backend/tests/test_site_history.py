import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.spatial import Basin, Wetland, Site
from app.models.sampling_record import SamplingRecord

client = TestClient(app)


def test_get_site_samplings_history(db_session: Session):
    # Setup test data
    basin = Basin(
        id=uuid.uuid4(),
        code="TEST_B",
        name="Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((34 -1, 35 -1, 35 0, 34 0, 34 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    wetland = Wetland(
        id=uuid.uuid4(),
        code="TEST_W",
        basin_id=basin.id,
        name="Test Wetland",
        geom=(
            "SRID=4326;MULTIPOLYGON(((34.1 -0.9, 34.9 -0.9, "
            "34.9 -0.1, 34.1 -0.1, 34.1 -0.9)))"
        ),
    )
    db_session.add(wetland)
    db_session.flush()

    site = Site(
        id=uuid.uuid4(),
        code="TEST_S",
        wetland_id=wetland.id,
        name="Test Site",
        description="A test site.",
        geom="SRID=4326;POINT(34.5 -0.5)",
    )
    db_session.add(site)
    db_session.flush()

    # Seed 3 sampling records
    now = datetime.utcnow()
    rec1 = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=7.20,
        temp_value=24.50,
        do_value=6.0,
        invasive_macrophytes=10.0,
        water_level="MEDIUM",
        sampled_at=now - timedelta(days=5),
    )
    rec2 = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=7.30,
        temp_value=25.00,
        do_value=6.5,
        invasive_macrophytes=12.0,
        water_level="MEDIUM",
        sampled_at=now - timedelta(days=2),
    )
    # This record is older than 30 days,
    # should be excluded by default date_from filter
    rec3 = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=6.90,
        temp_value=22.00,
        do_value=5.5,
        invasive_macrophytes=15.0,
        water_level="LOW",
        sampled_at=now - timedelta(days=40),
    )

    db_session.add_all([rec1, rec2, rec3])
    db_session.flush()

    # Test GET endpoint default (last 30 days)
    response = client.get(f"/api/v1/sites/{site.id}/samplings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Should be sorted asc
    assert data[0]["id"] == str(rec1.id)
    assert data[1]["id"] == str(rec2.id)
    assert "parameters" in data[0]
    assert data[0]["parameters"]["ph"]["value"] == 7.20

    # Test with custom date_from to include the older record
    date_from_str = (now - timedelta(days=45)).isoformat()
    response = client.get(
        f"/api/v1/sites/{site.id}/samplings?date_from={date_from_str}"
    )
    assert response.status_code == 200
    data_all = response.json()
    assert len(data_all) == 3
    assert data_all[0]["id"] == str(rec3.id)
