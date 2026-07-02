from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.form import (
    Form,
    QuestionGroup,
    Question,
    Option,
    FormPublishedVersion,
    FormStatus,
)
from app.schemas import form as schemas
from app.schemas.form import _normalize_blueprint_languages

from app.dependencies.auth import RoleChecker

router = APIRouter(prefix="/api/v1", tags=["form"])


# --- Form routes ---


@router.post(
    "/forms",
    response_model=schemas.FormResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def create_form(form: schemas.FormCreate, db: Session = Depends(get_db)):
    try:
        db_form = Form(name=form.name, type=form.type, status=form.status)
        db.add(db_form)
        db.commit()
        db.refresh(db_form)
        return db_form
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("/forms", response_model=List[schemas.FormResponse])
def list_forms(lang: Optional[str] = None, db: Session = Depends(get_db)):
    db_forms = db.query(Form).all()
    if lang:
        return [
            schemas.FormResponse.from_orm_localized(f, lang) for f in db_forms
        ]
    return db_forms


@router.get("/forms/{form_id}", response_model=schemas.FormDetailResponse)
def get_form(
    form_id: int, lang: Optional[str] = None, db: Session = Depends(get_db)
):
    db_form = db.query(Form).filter(Form.id == form_id).first()
    if not db_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
        )

    if lang:
        return schemas.FormDetailResponse.from_orm_localized(db_form, lang)

    # Filter active (non-deleted) groups and questions
    active_groups = [
        g for g in db_form.question_groups if g.deleted_at is None
    ]
    for g in active_groups:
        g.questions = [q for q in g.questions if q.deleted_at is None]

    db_form.question_groups = active_groups
    return db_form


@router.put(
    "/forms/{form_id}",
    response_model=schemas.FormBlueprintResponse,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def update_form(
    form_id: int,
    payload: schemas.FormBlueprintUpdate,
    db: Session = Depends(get_db),
):
    """Update a form and its question groups, questions, and options."""
    db_form = db.query(Form).filter(Form.id == form_id).first()
    if not db_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
        )

    try:
        # Update form basic info
        db_form.name = payload.name
        db_form.type = payload.type
        db_form.languages = payload.languages
        db_form.translations = payload.translations
        db_form.status = FormStatus.DRAFT.value

        # Get existing active groups
        existing_groups = (
            db.query(QuestionGroup)
            .filter(
                QuestionGroup.form_id == form_id,
                QuestionGroup.deleted_at.is_(None),
            )
            .all()
        )
        existing_group_ids = {g.id for g in existing_groups}

        # Track which group IDs are in the payload
        payload_group_ids = set()
        groups_data = payload.question_group or []

        # Get all existing active questions for the form to track
        # and update across groups
        existing_questions = (
            db.query(Question)
            .filter(
                Question.form_id == form_id,
                Question.deleted_at.is_(None),
            )
            .all()
        )
        existing_q_ids = {q.id for q in existing_questions}
        payload_q_ids = set()

        for g_order, g_data in enumerate(groups_data):
            questions_data = g_data.question or []

            if g_data.id and g_data.id in existing_group_ids:
                # Update existing group
                payload_group_ids.add(g_data.id)
                db_group = (
                    db.query(QuestionGroup)
                    .filter(QuestionGroup.id == g_data.id)
                    .first()
                )
                db_group.name = g_data.name
                db_group.label = g_data.label or g_data.description
                db_group.order = g_data.order if g_data.order else g_order
                db_group.repeatable = g_data.repeatable
                db_group.repeat_text = g_data.repeat_text
                db_group.translations = g_data.translations
            else:
                # Create new group
                db_group = QuestionGroup(
                    form_id=form_id,
                    name=g_data.name,
                    label=g_data.label or g_data.description,
                    order=g_data.order if g_data.order else g_order,
                    repeatable=g_data.repeatable,
                    repeat_text=g_data.repeat_text,
                    translations=g_data.translations,
                )
                db.add(db_group)
                db.flush()  # Get the ID

            for q_order, q_data in enumerate(questions_data):
                options_data = q_data.option or []
                # Handle string option (cascade reference)
                if isinstance(options_data, str):
                    options_data = []
                # Build extra dict for special fields
                extra = q_data.extra or {}
                if q_data.hidden_string:
                    extra["hiddenString"] = True
                if q_data.required_double_entry:
                    extra["requiredDoubleEntry"] = True
                if q_data.required_sign:
                    extra["requiredSign"] = q_data.required_sign
                if q_data.allow_other:
                    extra["allowOther"] = True
                if q_data.allow_other_text:
                    extra["allowOtherText"] = q_data.allow_other_text

                db_q = None
                if q_data.id:
                    db_q = (
                        db.query(Question)
                        .filter(Question.id == q_data.id)
                        .first()
                    )
                if not db_q and q_data.name:
                    # Find by name on this form prioritizing active questions
                    db_q = (
                        db.query(Question)
                        .filter(
                            Question.form_id == form_id,
                            Question.name == q_data.name,
                        )
                        .order_by(Question.deleted_at.asc().nullsfirst())
                        .first()
                    )

                if db_q:
                    # Update existing question
                    payload_q_ids.add(db_q.id)
                    db_q.question_group_id = db_group.id
                    db_q.name = q_data.name
                    db_q.label = q_data.label
                    db_q.short_label = q_data.short_label
                    db_q.type = q_data.type
                    db_q.required = q_data.required
                    db_q.order = q_order  # Respect current order in group
                    db_q.meta = q_data.meta
                    db_q.rule = q_data.rule
                    db_q.dependency = q_data.dependency
                    db_q.dependency_rule = q_data.dependency_rule
                    db_q.api = q_data.api
                    db_q.extra = extra if extra else q_data.extra
                    db_q.tooltip = q_data.tooltip
                    db_q.fn = q_data.fn
                    db_q.pre = q_data.pre
                    db_q.display_only = q_data.display_only
                    db_q.translations = q_data.translations
                    db_q.deleted_at = None  # Restore if soft-deleted
                    db.flush()
                else:
                    # Create new question
                    db_q = Question(
                        form_id=form_id,
                        question_group_id=db_group.id,
                        name=q_data.name,
                        label=q_data.label,
                        short_label=q_data.short_label,
                        type=q_data.type,
                        required=q_data.required,
                        order=q_data.order if q_data.order else q_order,
                        meta=q_data.meta,
                        rule=q_data.rule,
                        dependency=q_data.dependency,
                        dependency_rule=q_data.dependency_rule,
                        api=q_data.api,
                        extra=extra if extra else q_data.extra,
                        tooltip=q_data.tooltip,
                        fn=q_data.fn,
                        pre=q_data.pre,
                        display_only=q_data.display_only,
                        translations=q_data.translations,
                    )
                    db.add(db_q)
                    db.flush()
                    payload_q_ids.add(db_q.id)

                # Sync options within this question
                existing_options = (
                    db.query(Option)
                    .filter(Option.question_id == db_q.id)
                    .all()
                )
                existing_opt_ids = {o.id for o in existing_options}
                payload_opt_ids = set()

                for o_order, o_data in enumerate(options_data):
                    if isinstance(o_data, dict):
                        o_id = o_data.get("id")
                        o_label = o_data.get("label") or o_data.get("name")
                        o_value = o_data.get("value")
                        o_order_val = o_data.get("order", o_order)
                        o_other = o_data.get("other", False)
                        o_color = o_data.get("color")
                        o_translations = o_data.get("translations", [])
                    else:
                        # OptionUpdate object
                        o_id = o_data.id
                        o_label = o_data.label or o_data.name
                        o_value = o_data.value
                        o_order_val = o_data.order if o_data.order else o_order
                        o_other = o_data.other
                        o_color = o_data.color
                        o_translations = o_data.translations

                    if o_id and o_id in existing_opt_ids:
                        # Update existing option
                        payload_opt_ids.add(o_id)
                        db_opt = (
                            db.query(Option).filter(Option.id == o_id).first()
                        )
                        db_opt.label = o_label
                        db_opt.value = o_value
                        db_opt.order = o_order_val
                        db_opt.other = o_other
                        db_opt.color = o_color
                        db_opt.translations = o_translations
                    else:
                        # Create new option
                        db_opt = Option(
                            question_id=db_q.id,
                            label=o_label,
                            value=o_value,
                            order=o_order_val,
                            other=o_other,
                            color=o_color,
                            translations=o_translations,
                        )
                        db.add(db_opt)

                # Delete removed options
                for opt_id in existing_opt_ids - payload_opt_ids:
                    db.query(Option).filter(Option.id == opt_id).delete()

        # Flush all updates (including group changes) to DB
        # before running bulk soft-deletes
        db.flush()

        # Soft-delete removed questions (globally across the form)
        for q_id in existing_q_ids - payload_q_ids:
            db.query(Question).filter(Question.id == q_id).update(
                {Question.deleted_at: datetime.utcnow()},
                synchronize_session="fetch",
            )

        # Soft-delete removed groups
        for g_id in existing_group_ids - payload_group_ids:
            db.query(QuestionGroup).filter(QuestionGroup.id == g_id).update(
                {QuestionGroup.deleted_at: datetime.utcnow()},
                synchronize_session="fetch",
            )
            # Also soft-delete questions in removed groups
            db.query(Question).filter(
                Question.question_group_id == g_id
            ).update(
                {Question.deleted_at: datetime.utcnow()},
                synchronize_session="fetch",
            )

        db.commit()

        # Return updated blueprint
        active_groups = (
            db.query(QuestionGroup)
            .filter(
                QuestionGroup.form_id == form_id,
                QuestionGroup.deleted_at.is_(None),
            )
            .order_by(QuestionGroup.order.asc().nullslast())
            .all()
        )

        return schemas.FormBlueprintResponse.from_orm_model(
            db_form, active_groups
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get(
    "/forms/{form_id}/blueprint", response_model=schemas.FormBlueprintResponse
)
def get_form_blueprint(form_id: str, db: Session = Depends(get_db)):
    if form_id.isdigit():
        db_form = db.query(Form).filter(Form.id == int(form_id)).first()
    else:
        if form_id.lower() == "fgd":
            db_form = db.query(Form).filter(Form.name.ilike("%FGD%")).first()
        elif form_id.lower() == "lab-qa":
            db_form = db.query(Form).filter(Form.name.ilike("%Lab%")).first()
        else:
            db_form = (
                db.query(Form).filter(Form.name.ilike(f"%{form_id}%")).first()
            )

    if not db_form:
        raise HTTPException(
            status_code=404,
            detail=f"Form with identifier '{form_id}' not found",
        )

    if db_form.active_version and db_form.active_version.schema:
        schema = db_form.active_version.schema
        if isinstance(schema, dict) and "languages" in schema:
            schema["languages"] = _normalize_blueprint_languages(
                schema["languages"]
            )
            if "defaultLanguage" in schema and schema["defaultLanguage"]:
                from app.schemas.form import _to_editor_lang_code

                base = _to_editor_lang_code(str(schema["defaultLanguage"]))
                schema["defaultLanguage"] = (
                    base
                    if base in schema["languages"]
                    else (
                        schema["languages"][0] if schema["languages"] else "en"
                    )
                )
        return schema

    active_groups = (
        db.query(QuestionGroup)
        .filter(
            QuestionGroup.form_id == db_form.id,
            QuestionGroup.deleted_at.is_(None),
        )
        .order_by(QuestionGroup.order.asc().nullslast())
        .all()
    )

    return schemas.FormBlueprintResponse.from_orm_model(db_form, active_groups)


@router.get(
    "/forms/{form_id}/draft", response_model=schemas.FormBlueprintResponse
)
def get_form_draft(form_id: str, db: Session = Depends(get_db)):
    if form_id.isdigit():
        db_form = db.query(Form).filter(Form.id == int(form_id)).first()
    else:
        if form_id.lower() == "fgd":
            db_form = db.query(Form).filter(Form.name.ilike("%FGD%")).first()
        elif form_id.lower() == "lab-qa":
            db_form = db.query(Form).filter(Form.name.ilike("%Lab%")).first()
        else:
            db_form = (
                db.query(Form).filter(Form.name.ilike(f"%{form_id}%")).first()
            )

    if not db_form:
        raise HTTPException(
            status_code=404,
            detail=f"Form with identifier '{form_id}' not found",
        )

    active_groups = (
        db.query(QuestionGroup)
        .filter(
            QuestionGroup.form_id == db_form.id,
            QuestionGroup.deleted_at.is_(None),
        )
        .order_by(QuestionGroup.order.asc().nullslast())
        .all()
    )

    return schemas.FormBlueprintResponse.from_orm_model(db_form, active_groups)


@router.post(
    "/forms/{form_id}/publish",
    response_model=schemas.FormPublishedVersionResponse,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def publish_form(form_id: int, db: Session = Depends(get_db)):
    db_form = db.query(Form).filter(Form.id == form_id).first()
    if not db_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
        )

    # Fetch active groups and questions
    active_groups = (
        db.query(QuestionGroup)
        .filter(
            QuestionGroup.form_id == form_id,
            QuestionGroup.deleted_at.is_(None),
        )
        .order_by(QuestionGroup.order.asc().nullslast())
        .all()
    )

    schema_snapshot = schemas.FormBlueprintResponse.from_orm_model(
        db_form, active_groups
    ).model_dump()

    # Increment version
    next_version = (
        db.query(FormPublishedVersion).filter_by(form_id=form_id).count() or 0
    ) + 1

    try:
        published_version = FormPublishedVersion(
            form_id=form_id,
            version=next_version,
            schema=schema_snapshot,
            published_at=datetime.utcnow(),
        )
        db.add(published_version)
        db.commit()
        db.refresh(published_version)

        # Update Form attributes
        db_form.published_at = datetime.utcnow()
        db_form.version = next_version
        db_form.status = FormStatus.PUBLISHED.value
        db_form.active_version_id = published_version.id
        db.commit()

        return published_version
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


# --- Question Group routes ---


@router.post(
    "/question-groups",
    response_model=schemas.QuestionGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def create_question_group(
    group: schemas.QuestionGroupCreate, db: Session = Depends(get_db)
):
    # Check if parent form exists
    form_exists = db.query(Form).filter(Form.id == group.form_id).first()
    if not form_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent form does not exist",
        )

    # Check if active group with same name already exists
    existing = (
        db.query(QuestionGroup)
        .filter(
            QuestionGroup.form_id == group.form_id,
            QuestionGroup.name == group.name,
            QuestionGroup.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active group with this name already exists",
        )

    try:
        db_group = QuestionGroup(
            form_id=group.form_id,
            name=group.name,
            label=group.label,
            order=group.order,
            repeatable=group.repeatable,
            repeat_text=group.repeat_text,
        )
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.delete(
    "/question-groups/{group_id}",
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def delete_question_group(group_id: int, db: Session = Depends(get_db)):
    db_group = (
        db.query(QuestionGroup).filter(QuestionGroup.id == group_id).first()
    )
    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question group not found",
        )

    try:
        db_group.deleted_at = datetime.utcnow()
        # Soft delete questions inside group as well
        db.query(Question).filter(
            Question.question_group_id == group_id
        ).update(
            {Question.deleted_at: datetime.utcnow()},
            synchronize_session="fetch",
        )
        db.commit()
        return {"message": "Question group soft-deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


# --- Question routes ---


@router.post(
    "/questions",
    response_model=schemas.QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def create_question(
    question: schemas.QuestionCreate, db: Session = Depends(get_db)
):
    # Check if parent form exists
    form_exists = db.query(Form).filter(Form.id == question.form_id).first()
    if not form_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent form does not exist",
        )

    # Check if parent group exists
    group_exists = (
        db.query(QuestionGroup)
        .filter(QuestionGroup.id == question.question_group_id)
        .first()
    )
    if not group_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question group does not exist",
        )

    # Check if active question with same name already exists under the form
    existing = (
        db.query(Question)
        .filter(
            Question.form_id == question.form_id,
            Question.name == question.name,
            Question.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active question with this name already exists",
        )

    try:
        rule = question.rule or {}
        if question.validation_min is not None:
            rule["min"] = question.validation_min
        if question.validation_max is not None:
            rule["max"] = question.validation_max

        db_q = Question(
            form_id=question.form_id,
            question_group_id=question.question_group_id,
            name=question.name,
            label=question.label,
            short_label=question.short_label,
            type=question.type,
            required=question.required,
            order=question.order,
            meta=question.meta,
            rule=rule if rule else None,
            dependency=question.dependency,
            dependency_rule=question.dependency_rule,
            api=question.api,
            extra=question.extra,
            tooltip=question.tooltip,
            fn=question.fn,
            pre=question.pre,
            display_only=question.display_only,
        )
        db.add(db_q)
        db.commit()
        db.refresh(db_q)
        return db_q
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.delete(
    "/questions/{question_id}",
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def delete_question(question_id: int, db: Session = Depends(get_db)):
    db_q = db.query(Question).filter(Question.id == question_id).first()
    if not db_q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )

    try:
        db_q.deleted_at = datetime.utcnow()
        db.commit()
        return {"message": "Question soft-deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


# --- Option routes ---


@router.post(
    "/options",
    response_model=schemas.OptionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["Admin"]))],
)
def create_option(option: schemas.OptionCreate, db: Session = Depends(get_db)):
    # Check if parent question exists
    q_exists = (
        db.query(Question).filter(Question.id == option.question_id).first()
    )
    if not q_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question does not exist",
        )

    # Check if value already exists for this question
    existing = (
        db.query(Option)
        .filter(
            Option.question_id == option.question_id,
            Option.value == option.value,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Option with this value already exists for this question",
        )

    try:
        db_opt = Option(
            question_id=option.question_id,
            label=option.label,
            value=option.value,
            order=option.order,
            other=option.other,
            color=option.color,
        )
        db.add(db_opt)
        db.commit()
        db.refresh(db_opt)
        return db_opt
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
