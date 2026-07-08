from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from app.models.form import (
    Form,
    QuestionGroup,
    Question,
    Option,
)
from app.seeds.form_seeder_helper import seed_forms


def test_seed_forms_success(db_session: Session):
    # 1. Run the seeder
    seed_forms(db_session)

    # 2. Assert Forms created
    forms = db_session.query(Form).all()
    assert len(forms) == 5

    form_names = [f.name for f in forms]
    assert "Pollution Reporting Form" in form_names
    assert "Monthly Wetland Sampling" in form_names
    assert "Indigenous Knowledge Record" in form_names
    assert "Lab QA Report" in form_names
    assert "External Satellite & Climate Data" in form_names

    # Check specific form details (e.g. Pollution Reporting Form)
    pollution_form = (
        db_session.query(Form)
        .filter(Form.name == "Pollution Reporting Form")
        .first()
    )
    assert pollution_form is not None
    assert pollution_form.status == 2  # Published
    assert pollution_form.version == 1

    # Check QuestionGroups
    groups = (
        db_session.query(QuestionGroup)
        .filter(QuestionGroup.form_id == pollution_form.id)
        .all()
    )
    assert len(groups) == 1
    assert groups[0].name == "Incident Details"

    # Check Questions
    questions = (
        db_session.query(Question)
        .filter(Question.form_id == pollution_form.id)
        .all()
    )
    assert len(questions) == 3
    q_names = [q.name for q in questions]
    assert "incident_type" in q_names
    assert "location_id" in q_names

    # Check Options mapping
    incident_type_q = (
        db_session.query(Question)
        .filter(
            Question.form_id == pollution_form.id,
            Question.name == "incident_type",
        )
        .first()
    )
    assert incident_type_q is not None
    assert incident_type_q.type == "option"  # Option type

    options = (
        db_session.query(Option)
        .filter(Option.question_id == incident_type_q.id)
        .all()
    )
    assert len(options) == 6
    assert options[0].label == "Water colour (darker/murkier)"
    assert options[0].value == "1"

    # Check Cascade question api endpoint configuration
    location_q = (
        db_session.query(Question)
        .filter(
            Question.form_id == pollution_form.id,
            Question.name == "location_id",
        )
        .first()
    )
    assert location_q is not None
    assert location_q.type == "cascade"  # Cascade type
    assert location_q.api is not None
    assert location_q.api.get("endpoint") == "/api/v1/reference/sub-counties"

    # Check GEE Satellite Form
    gee_form = (
        db_session.query(Form)
        .filter(Form.name == "External Satellite & Climate Data")
        .first()
    )
    assert gee_form is not None
    assert len(gee_form.question_groups) == 2

    # Check Indigenous Knowledge Record compliance details
    ik_form = (
        db_session.query(Form)
        .filter(Form.name == "Indigenous Knowledge Record")
        .first()
    )
    assert ik_form is not None
    assert len(ik_form.question_groups) == 3

    # Check Contextual Metadata questions
    meta_group = [
        g for g in ik_form.question_groups if g.name == "Contextual Metadata"
    ][0]
    assert len(meta_group.questions) == 6
    meta_q_names = [q.name for q in meta_group.questions]
    assert "wetland_id" in meta_q_names
    assert "land_use" in meta_q_names
    assert "area" in meta_q_names

    # Check Fuzzy Logic Dimensions questions and option values
    fuzzy_group = [
        g
        for g in ik_form.question_groups
        if g.name == "Fuzzy Logic Dimensions"
    ][0]
    assert len(fuzzy_group.questions) == 7
    bio_q = [
        q for q in fuzzy_group.questions if q.name == "biodiversity_change"
    ][0]
    assert bio_q.type == "option"
    assert len(bio_q.options) == 3
    bio_opt_values = sorted([float(opt.value) for opt in bio_q.options])
    assert bio_opt_values == [0.3, 0.6, 1.0]

    # Check Historical and Local Practices questions
    hist_group = [
        g
        for g in ik_form.question_groups
        if g.name == "Historical and Local Practices"
    ][0]
    assert len(hist_group.questions) == 6
    hist_q_names = [q.name for q in hist_group.questions]
    assert "earlier_fish_types" in hist_q_names
    assert "historical_prediction_methods" in hist_q_names
    assert "soil_moisture_preservation" in hist_q_names

    # 3. Test Idempotency (run seeder again)
    seed_forms(db_session)

    # Should not duplicate the base entities (except versions snapshots)
    forms_after = db_session.query(Form).all()
    assert len(forms_after) == 5

    pollution_form_after = (
        db_session.query(Form)
        .filter(Form.name == "Pollution Reporting Form")
        .first()
    )
    assert pollution_form_after.version == 2  # New published snapshot version


def test_seed_form_v2_and_cleanup(db_session: Session):
    from unittest.mock import patch
    import json

    # 1. First run default seeder to populate default forms (v1 format)
    seed_forms(db_session)

    # Verify initial questions count for Monthly Wetland Sampling
    sampling_form = (
        db_session.query(Form)
        .filter(Form.name == "Monthly Wetland Sampling")
        .first()
    )
    assert sampling_form is not None
    q_count_before = (
        db_session.query(Question)
        .filter(
            Question.form_id == sampling_form.id, Question.deleted_at.is_(None)
        )
        .count()
    )
    assert q_count_before > 0

    # 2. Run with the v2 form JSON which includes label-based fields
    # Patch json.load to map form_id dynamically to handle DB sequence changes
    original_json_load = json.load

    def mocked_json_load(fp):
        data = original_json_load(fp)
        if isinstance(data, dict) and "Monthly Wetland Sampling" in data.get(
            "name", ""
        ):
            data = data.copy()
            data["form_id"] = sampling_form.id
            # Also update name to match sampling_form.name
            # so it updates in-place
            data["name"] = sampling_form.name
        return data

    with patch("json.load", side_effect=mocked_json_load):
        seed_forms(
            db_session,
            filename_filter="form_pipeline_b_citizen_scientist_v2.json",
        )

    # Fetch form again to inspect updates
    db_session.expire_all()
    updated_form = (
        db_session.query(Form)
        .filter(Form.name == "Monthly Wetland Sampling")
        .first()
    )
    assert updated_form is not None

    # Verify questions under updated form
    active_questions = (
        db_session.query(Question)
        .filter(
            Question.form_id == updated_form.id, Question.deleted_at.is_(None)
        )
        .all()
    )
    q_names = [q.name for q in active_questions]
    # Verify new schema questions exist
    assert "water_color" in q_names
    assert "water_smell" in q_names
    assert "main_activities_observed" in q_names

    # Verify that the label is correctly mapped from the JSON "label" field
    water_color_q = (
        db_session.query(Question)
        .filter(
            Question.form_id == updated_form.id, Question.name == "water_color"
        )
        .first()
    )
    assert water_color_q is not None
    assert water_color_q.label == "Water color"

    # Verify that obsolete questions not present in v2 JSON are soft-deleted
    # For example, "crops" is present in v1 but removed/changed in v2.
    deleted_crops_q = (
        db_session.query(Question)
        .filter(
            Question.form_id == updated_form.id,
            Question.name == "crops",
        )
        .first()
    )
    assert deleted_crops_q is not None
    assert deleted_crops_q.deleted_at is not None


def test_seed_spatial_success(db_session: Session):
    from app.seeds.spatial_seeder_helper import seed_spatial
    from app.models.spatial import Basin, Wetland, Site, SpatialBoundary

    # 1. Run spatial seeder
    seed_spatial(db_session)

    # 2. Assert Basins created
    basins = db_session.query(Basin).all()
    assert len(basins) == 2
    basin_ids = [b.code for b in basins]
    assert "MARA" in basin_ids
    assert "SIO_SITEKO" in basin_ids

    # 3. Assert Wetlands created
    wetlands = db_session.query(Wetland).all()
    assert len(wetlands) == 2
    wetland_ids = [w.code for w in wetlands]
    assert "Mara_Wetland" in wetland_ids
    assert "Sio_Siteko_Wetland" in wetland_ids

    # 4. Assert Sites created
    sites = db_session.query(Site).all()
    assert len(sites) == 8
    site_ids = [s.code for s in sites]
    assert "NBD-MARA-001" in site_ids
    assert "NBD-MARA-004" in site_ids
    assert "NBD-SIO-001" in site_ids
    assert "NBD-SIO-004" in site_ids

    # Assert Management Actions per site: 2 GREEN, 4 YELLOW, 4 RED = 10 total
    from app.models.management_action import ManagementAction

    seeded_site_ids = [s.id for s in sites]
    actions = (
        db_session.query(ManagementAction)
        .filter(ManagementAction.site_id.in_(seeded_site_ids))
        .all()
    )
    assert len(actions) == 80

    # 5. Assert Sub-counties created
    sub_counties = db_session.query(SpatialBoundary).all()
    assert len(sub_counties) == 28

    mara_sub_counties = [
        s.name for s in sub_counties if s.basin.code == "MARA"
    ]
    sio_sub_counties = [
        s.name for s in sub_counties if s.basin.code == "SIO_SITEKO"
    ]

    assert sorted(mara_sub_counties) == sorted(
        [
            "Mara Region",
            "Nakuru",
            "Narok",
            "Bomet",
            "Kuresoi South",
            "Kilgoris",
            "Narok West",
            "Narok North",
            "Narok South",
            "Bomet Central",
            "Konoin",
            "Molo",
            "Emurua Dikirr",
            "Chepalungu",
            "Bomet East",
        ]
    )
    assert sorted(sio_sub_counties) == sorted(
        [
            "Sio-Siteko Region",
            "Kakamega",
            "Busia",
            "Bungoma",
            "Matungu",
            "Budalangi",
            "Funyula",
            "Teso South",
            "Butula",
            "Bumula",
            "Matayos",
            "Nambale",
            "Kanduyi",
        ]
    )

    # Verify high-fidelity GeoJSON geometries loaded
    lower_mara = (
        db_session.query(Wetland)
        .filter(Wetland.code == "Mara_Wetland")
        .first()
    )
    sio_estuary = (
        db_session.query(Wetland)
        .filter(Wetland.code == "Sio_Siteko_Wetland")
        .first()
    )
    assert lower_mara is not None
    assert sio_estuary is not None

    lower_mara_shp = to_shape(lower_mara.geom)
    sio_estuary_shp = to_shape(sio_estuary.geom)
    assert lower_mara_shp.geom_type == "MultiPolygon"
    assert sio_estuary_shp.geom_type == "MultiPolygon"
    assert len(lower_mara_shp.geoms[0].exterior.coords) > 5

    # 6. Test Idempotency
    seed_spatial(db_session)
    assert len(db_session.query(Basin).all()) == 2
    assert len(db_session.query(Wetland).all()) == 2
    assert len(db_session.query(Site).all()) == 8
    assert len(db_session.query(SpatialBoundary).all()) == 28
