from sqlalchemy.orm import Session
from app.models.form import (
    Form,
    QuestionGroup,
    Question,
    Option,
)
from app.seeds.seeder import seed_forms


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
    assert len(questions) == 2
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
    assert len(options) == 5
    assert options[0].label == "Water colour suddenly became darker/murkier"
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
    assert len(meta_group.questions) == 5
    meta_q_names = [q.name for q in meta_group.questions]
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
