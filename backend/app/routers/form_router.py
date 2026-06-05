from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.form import (
    Form,
    QuestionGroup,
    Question,
    Option,
    FormPublishedVersion,
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
def list_forms(db: Session = Depends(get_db)):
    return db.query(Form).all()


@router.get("/forms/{form_id}", response_model=schemas.FormDetailResponse)
def get_form(form_id: int, db: Session = Depends(get_db)):
    db_form = db.query(Form).filter(Form.id == form_id).first()
    if not db_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Form not found"
        )

    # Filter active (non-deleted) groups and questions
    active_groups = [
        g for g in db_form.question_groups if g.deleted_at is None
    ]
    for g in active_groups:
        g.questions = [q for q in g.questions if q.deleted_at is None]

    db_form.question_groups = active_groups
    return db_form


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

    question_groups_schema = []
    for g in active_groups:
        active_questions = (
            db.query(Question)
            .filter(
                Question.question_group_id == g.id,
                Question.deleted_at.is_(None),
            )
            .order_by(Question.order.asc().nullslast())
            .all()
        )

        questions_schema = []
        for q in active_questions:
            options_schema = []
            for opt in q.options:
                options_schema.append(
                    {
                        "id": opt.id,
                        "label": opt.label,
                        "value": opt.value,
                        "order": opt.order,
                        "other": opt.other,
                        "color": opt.color,
                    }
                )

            questions_schema.append(
                {
                    "id": q.id,
                    "name": q.name,
                    "label": q.label,
                    "short_label": q.short_label,
                    "type": q.type,
                    "required": q.required,
                    "rule": q.rule,
                    "dependency": q.dependency,
                    "dependency_rule": q.dependency_rule,
                    "api": q.api,
                    "extra": q.extra,
                    "tooltip": q.tooltip,
                    "fn": q.fn,
                    "pre": q.pre,
                    "display_only": q.display_only,
                    "options": options_schema,
                }
            )

        question_groups_schema.append(
            {
                "id": g.id,
                "name": g.name,
                "label": g.label,
                "order": g.order,
                "repeatable": g.repeatable,
                "repeat_text": g.repeat_text,
                "questions": questions_schema,
            }
        )

    schema_snapshot = {
        "form_id": db_form.id,
        "name": db_form.name,
        "version": db_form.version,
        "question_groups": question_groups_schema,
    }

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
        db_form.status = 2  # status: Published (matching reference FormStatus)
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
