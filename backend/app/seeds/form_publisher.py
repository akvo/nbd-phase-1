import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.form import (
    Form,
    QuestionGroup,
    Question,
    FormPublishedVersion,
    FormStatus,
)

logger = logging.getLogger(__name__)


def publish_form_snapshot(form: Form, db: Session):
    # Fetch active groups and questions
    active_groups = (
        db.query(QuestionGroup)
        .filter(
            QuestionGroup.form_id == form.id,
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
        "form_id": form.id,
        "name": form.name,
        "version": form.version,
        "question_groups": question_groups_schema,
    }

    # Increment version
    next_version = (
        db.query(FormPublishedVersion).filter_by(form_id=form.id).count() or 0
    ) + 1

    published_version = FormPublishedVersion(
        form_id=form.id,
        version=next_version,
        schema=schema_snapshot,
        published_at=datetime.utcnow(),
    )
    db.add(published_version)
    db.flush()

    form.published_at = datetime.utcnow()
    form.version = next_version
    form.status = FormStatus.PUBLISHED.value
    form.active_version_id = published_version.id
    db.flush()
    logger.info(
        "Published Form snapshot version %s for: %s", next_version, form.name
    )
