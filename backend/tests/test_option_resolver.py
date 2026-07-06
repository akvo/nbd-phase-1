from sqlalchemy.orm import Session
from app.models.form import Form, Question, Option, QuestionType
from app.models.submission import Datapoint, Answer
from app.models.spatial import Basin, SpatialBoundary
from app.services.option_resolver import populate_answers_option_labels


def test_option_resolver_scenarios(db_session: Session):
    # 1. Setup Form, Question, and Options
    basin = Basin(
        code="test_basin_opt",
        name="Test Basin Opt",
        geom="SRID=4326;MULTIPOLYGON(((30 -1, 31 -1, 31 0, 30 0, 30 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    from app.models.form import QuestionGroup

    form = Form(name="Test Options Form", type=1)
    db_session.add(form)
    db_session.flush()

    group = QuestionGroup(
        form_id=form.id,
        name="test_group",
        label="Test Group",
        order=1,
    )
    db_session.add(group)
    db_session.flush()

    # Question 1: single select option
    q_opt = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="incident_type",
        label="Incident Type",
        type=QuestionType.option.value,
        order=1,
    )
    db_session.add(q_opt)
    db_session.flush()

    # Question 2: select multiple option
    q_mult = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="activities",
        label="Activities",
        type=QuestionType.multiple_option.value,
        order=2,
    )
    db_session.add(q_mult)
    db_session.flush()

    # Seed Options for Incident Type
    opt_smell = Option(
        question_id=q_opt.id,
        label="Smell",
        value="smell",
        order=1,
    )
    opt_color = Option(
        question_id=q_opt.id,
        label="Color",
        value="color",
        order=2,
    )
    db_session.add_all([opt_smell, opt_color])

    # Seed Options for Activities (including one containing a space)
    opt_sugarcane = Option(
        question_id=q_mult.id,
        label="Intensive Sugarcane",
        value="sugarcane",
        order=1,
    )
    opt_potato = Option(
        question_id=q_mult.id,
        label="Intensive Potato",
        value="potato",
        order=2,
    )
    opt_space_val = Option(
        question_id=q_mult.id,
        label="North America",
        value="north america",
        order=3,
    )
    db_session.add_all([opt_sugarcane, opt_potato, opt_space_val])

    # Seed Spatial boundary for cascade checks
    region = SpatialBoundary(
        name="Mara Region",
        level=1,
        basin_id=basin.id,
    )
    db_session.add(region)
    db_session.flush()

    county = SpatialBoundary(
        name="Bomet County",
        level=2,
        parent_id=region.id,
        basin_id=basin.id,
    )
    db_session.add(county)
    db_session.flush()

    q_cascade = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="location",
        label="Location",
        type=QuestionType.cascade.value,
        order=3,
    )
    db_session.add(q_cascade)
    db_session.flush()

    db_session.commit()

    # 2. Setup Datapoint and Answers to test
    dp = Datapoint(
        form_id=form.id,
        basin_id=basin.id,
        name="test_dp",
    )
    db_session.add(dp)
    db_session.flush()

    # Case 1: Match by Option ID (database primary key integer)
    ans_opt_id = Answer(
        datapoint_id=dp.id,
        question_id=q_opt.id,
        options=[opt_color.id],
        index=0,
    )

    # Case 2: Match by Option Value (Kobo string value)
    ans_opt_val = Answer(
        datapoint_id=dp.id,
        question_id=q_opt.id,
        options=["smell"],
        index=1,
    )

    # Case 3: Space-separated splitting match (select_multiple from Kobo)
    ans_mult_split = Answer(
        datapoint_id=dp.id,
        question_id=q_mult.id,
        options=["sugarcane potato"],
        index=0,
    )

    # Case 4: Space-containing value safeguard (matches directly, no split)
    ans_space_val = Answer(
        datapoint_id=dp.id,
        question_id=q_mult.id,
        options=["north america"],
        index=1,
    )

    # Case 5: UUID Spatial Boundary Match
    ans_cascade = Answer(
        datapoint_id=dp.id,
        question_id=q_cascade.id,
        options=[str(county.id)],
        index=0,
    )

    db_session.add_all(
        [
            ans_opt_id,
            ans_opt_val,
            ans_mult_split,
            ans_space_val,
            ans_cascade,
        ]
    )
    db_session.flush()

    # Run the resolver
    populate_answers_option_labels([dp], db_session)

    # Assertions
    # Case 1 resolved label
    assert ans_opt_id._resolved_value == "Color"

    # Case 2 resolved label
    assert ans_opt_val._resolved_value == "Smell"

    # Case 3 resolved label (space-separated, splits and joins)
    assert (
        ans_mult_split._resolved_value
        == "Intensive Sugarcane, Intensive Potato"
    )

    # Case 4 resolved label (has space but matches directly, no split)
    assert ans_space_val._resolved_value == "North America"

    # Case 5 resolved label (UUID lookup)
    assert ans_cascade._resolved_value == "Bomet County"


def test_resolve_datapoint_brief_attributes(db_session: Session):
    from app.services.option_resolver import resolve_datapoint_brief_attributes

    # Setup Form, Question, and Options
    basin = Basin(
        code="brief_test_basin",
        name="Brief Test Basin",
        geom="SRID=4326;MULTIPOLYGON(((30 -1, 31 -1, 31 0, 30 0, 30 -1)))",
    )
    db_session.add(basin)
    db_session.flush()

    form = Form(name="Brief Test Form", type=1)
    db_session.add(form)
    db_session.flush()

    from app.models.form import QuestionGroup

    group = QuestionGroup(
        form_id=form.id,
        name="brief_group",
        label="Brief Group",
        order=1,
    )
    db_session.add(group)
    db_session.flush()

    q_type = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="incident_type",
        label="Incident Type",
        type=QuestionType.option.value,
        order=1,
    )
    q_loc = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="location_id",
        label="Location ID",
        type=QuestionType.cascade.value,
        order=2,
    )
    q_img = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="photo",
        label="Photo",
        type=QuestionType.image.value,
        order=3,
    )
    db_session.add_all([q_type, q_loc, q_img])
    db_session.flush()

    opt_type = Option(
        question_id=q_type.id,
        label="Fish kill",
        value="fish_kill",
        order=1,
    )
    db_session.add(opt_type)
    db_session.flush()

    sb_loc = SpatialBoundary(
        name="Mara North",
        level=1,
        basin_id=basin.id,
    )
    db_session.add(sb_loc)
    db_session.flush()

    # Datapoint
    dp = Datapoint(
        form_id=form.id,
        basin_id=basin.id,
        status="APPROVED",
    )
    db_session.add(dp)
    db_session.flush()

    ans_img = Answer(
        datapoint_id=dp.id,
        question_id=q_img.id,
        name="media/webforms/test.jpg",
        index=0,
    )
    ans_type = Answer(
        datapoint_id=dp.id,
        question_id=q_type.id,
        name="incident_type",
        options=["fish_kill"],
        index=1,
    )
    ans_loc = Answer(
        datapoint_id=dp.id,
        question_id=q_loc.id,
        name="location_id",
        options=[str(sb_loc.id)],
        index=2,
    )
    db_session.add_all([ans_img, ans_type, ans_loc])
    db_session.flush()

    # Debug assertions to check database state
    type_ans_debug = (
        db_session.query(Answer)
        .join(Question, Answer.question_id == Question.id)
        .filter(
            Answer.datapoint_id == dp.id,
            Question.name == "incident_type",
        )
        .first()
    )
    assert type_ans_debug is not None
    assert type_ans_debug.options == ["fish_kill"]

    opt_debug = (
        db_session.query(Option)
        .filter(
            Option.question_id == type_ans_debug.question_id,
            Option.value == "fish_kill",
        )
        .first()
    )
    assert opt_debug is not None
    assert opt_debug.label == "Fish kill"

    # Test with brief=True
    # (queries database for Answers since datapoint.answers is not loaded)
    image_url, type_name, type_id, location = (
        resolve_datapoint_brief_attributes(dp, db_session, brief=True)
    )
    assert image_url.startswith(
        "/api/v1/storage/files/media/webforms/test.jpg"
    )
    assert type_name == "Fish kill"
    assert type_id == "fish_kill"
    assert location == "Mara North"

    # Test with brief=False (uses datapoint.answers relationship)
    # Simulate populated answers
    ans_img.read_url = "media/webforms/test.jpg"
    dp.answers = [ans_img, ans_type, ans_loc]
    # Set resolved values just like populate_answers_option_labels does
    ans_loc._resolved_value = "Mara North"
    ans_type._resolved_value = "Fish kill"

    image_url_f, type_name_f, type_id_f, location_f = (
        resolve_datapoint_brief_attributes(dp, db_session, brief=False)
    )
    assert image_url_f == "media/webforms/test.jpg"
    assert type_name_f == "Fish kill"
    assert type_id_f == "fish_kill"
    assert location_f == "Mara North"
