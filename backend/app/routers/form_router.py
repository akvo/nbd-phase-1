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
        return db_form.active_version.schema

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
