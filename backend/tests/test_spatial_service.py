from sqlalchemy.orm import Session
from app.models.spatial import Basin, SpatialBoundary
from app.services.spatial_service import (
    get_root_boundaries,
    get_child_boundaries,
    has_child_boundaries,
    get_boundary_by_id,
)


def test_spatial_service_hierarchy_queries(db_session: Session):
    # 1. Setup test basin, region, county, subcounty, ward
    basin = Basin(
        code="TEST-SERVICE-BASIN",
        name="Service Basin",
        geom="SRID=4326;MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))",
    )
    db_session.add(basin)
    db_session.flush()

    county = SpatialBoundary(
        name="County A", level=2, basin_id=basin.id, parent_id=None
    )
    db_session.add(county)
    db_session.flush()

    sub_county = SpatialBoundary(
        name="Sub-County A1", level=3, basin_id=basin.id, parent_id=county.id
    )
    db_session.add(sub_county)
    db_session.flush()

    ward = SpatialBoundary(
        name="Ward A1a", level=4, basin_id=basin.id, parent_id=sub_county.id
    )
    db_session.add(ward)
    db_session.commit()

    # 2. Test get_root_boundaries
    roots = get_root_boundaries(db_session, basin_codes=["TEST-SERVICE-BASIN"])
    assert len(roots) == 1
    assert roots[0].name == "County A"

    # 3. Test get_child_boundaries
    children_county = get_child_boundaries(db_session, str(county.id))
    assert len(children_county) == 1
    assert children_county[0].name == "Sub-County A1"

    children_ward = get_child_boundaries(db_session, str(ward.id))
    assert len(children_ward) == 0

    # 4. Test has_child_boundaries
    assert has_child_boundaries(db_session, str(county.id)) is True
    assert has_child_boundaries(db_session, str(sub_county.id)) is True
    assert has_child_boundaries(db_session, str(ward.id)) is False

    # 5. Test get_boundary_by_id
    found_ward = get_boundary_by_id(db_session, str(ward.id))
    assert found_ward is not None
    assert found_ward.name == "Ward A1a"
