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

    # Question 2: select multiple option (allow_other=True)
    q_mult = Question(
        form_id=form.id,
        question_group_id=group.id,
        name="activities",
        label="Activities",
        type=QuestionType.multiple_option.value,
        order=2,
        extra={"allowOther": True, "allowOtherText": "Others, please specify"},
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

    # Case 6: allow_other — 'other' token replaced by free-text from ans.name
    ans_allow_other = Answer(
        datapoint_id=dp.id,
        question_id=q_mult.id,
        options=["sugarcane", "other"],
        name="spring fed pond",
        index=2,
    )

    # Case 7: XLSForm or_other uses '_other' token (underscore prefix)
    ans_allow_other_underscore = Answer(
        datapoint_id=dp.id,
        question_id=q_mult.id,
        options=["potato", "_other"],
        name="lotus plant",
        index=3,
    )

    db_session.add_all(
        [
            ans_opt_id,
            ans_opt_val,
            ans_mult_split,
            ans_space_val,
            ans_cascade,
            ans_allow_other,
            ans_allow_other_underscore,
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

    # Case 6: allow_other — 'other' token replaced by free-text from ans.name
    assert ans_allow_other._resolved_value == (
        "Intensive Sugarcane, Other: spring fed pond"
    )

    # Case 7: XLSForm '_other' token (underscore prefix) also resolved
    assert ans_allow_other_underscore._resolved_value == (
        "Intensive Potato, Other: lotus plant"
    )
