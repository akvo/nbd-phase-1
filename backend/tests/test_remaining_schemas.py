import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.spatial import Basin, Wetland, Site
from app.models.management_action import ManagementAction
from app.models.citizen import Citizen
from app.models.sampling_record import SamplingRecord
from app.models.fgd_record import FgdRecord
from app.models.health_score import HealthScore


def test_create_remaining_schemas(db_session: Session):
    # 1. Setup spatial anchors
    basin = Basin(
        code="MARA-TEST",
        name="Mara Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5)))",
    )
    db_session.add(basin)
    db_session.commit()

    wetland = Wetland(
        code="WET-TEST",
        basin_id=basin.id,
        name="Test Wetland",
        geom="SRID=4326;POLYGON((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5))",
    )
    db_session.add(wetland)
    db_session.commit()

    site = Site(
        code="SITE-TEST",
        wetland_id=wetland.id,
        name="Test Site",
        geom="SRID=4326;POINT(34.5212 -1.4589)",
    )
    db_session.add(site)
    db_session.commit()

    # 2. Test ManagementAction persistence
    action = ManagementAction(
        site_id=site.id,
        status_color="GREEN",
        short_label="Test Action",
        description_text="This is a test recommendation action",
    )
    db_session.add(action)
    db_session.commit()
    assert action.id is not None
    assert action.site_id == site.id

    # 3. Test Citizen persistence
    citizen = Citizen(
        phone_number="+254700000000", site_id=site.id, role="WATCHER"
    )
    db_session.add(citizen)
    db_session.commit()
    assert citizen.id is not None
    assert citizen.site_id == site.id

    # 4. Test SamplingRecord persistence
    sampling = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=7.2,
        temp_value=24.5,
        do_value=6.8,
        invasive_macrophytes=12.5,
        cpue_value=1.5,
        water_level="MEDIUM",
        sampled_at=datetime.utcnow(),
    )
    db_session.add(sampling)
    db_session.commit()
    assert sampling.site_id == site.id
    assert float(sampling.ph_value) == 7.2

    # 5. Test FgdRecord persistence
    fgd = FgdRecord(
        id=uuid.uuid4(),
        wetland_id=wetland.id,
        fish_abundance="Same",
        water_clarity="Somewhat Worse",
        vegetation_cover="Partial Loss",
        conducted_at=datetime.utcnow(),
    )
    db_session.add(fgd)
    db_session.commit()
    assert fgd.wetland_id == wetland.id

    # 6. Test HealthScore persistence
    score = HealthScore(
        site_id=site.id,
        wqi_score=0.85,
        composite_score=0.78,
        ik_signal_value=0.60,
        adjusted_score=0.75,
        health_class="B",
        calculated_at=datetime.utcnow(),
    )
    db_session.add(score)
    db_session.commit()
    assert score.id is not None
    assert score.site_id == site.id


def test_sampling_record_limits_constraint(db_session: Session):
    # Test physical constraints boundary error (ph_value limit check constraint)
    basin = Basin(
        code="MARA-LIMITS",
        name="Mara Limits Basin",
        geom="SRID=4326;MULTIPOLYGON(((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5)))",
    )
    db_session.add(basin)
    db_session.commit()

    wetland = Wetland(
        code="WET-LIMITS",
        basin_id=basin.id,
        name="Limits Wetland",
        geom="SRID=4326;POLYGON((34.5 -1.5, 34.6 -1.5, 34.6 -1.4, 34.5 -1.4, 34.5 -1.5))",
    )
    db_session.add(wetland)
    db_session.commit()

    site = Site(
        code="SITE-LIMITS",
        wetland_id=wetland.id,
        name="Limits Site",
        geom="SRID=4326;POINT(34.5212 -1.4589)",
    )
    db_session.add(site)
    db_session.commit()

    # Out of range pH (11.0, allowed range is 2.0 to 10.0)
    invalid_sampling = SamplingRecord(
        id=uuid.uuid4(),
        site_id=site.id,
        ph_value=11.0,
        temp_value=24.5,
        do_value=6.8,
        invasive_macrophytes=12.5,
        water_level="MEDIUM",
        sampled_at=datetime.utcnow(),
    )
    db_session.add(invalid_sampling)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
