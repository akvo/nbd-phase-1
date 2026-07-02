import os
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.form import (
    Form,
    QuestionGroup,
    Question,
    Option,
    QuestionType,
)
from app.seeds.form_publisher import publish_form_snapshot

logger = logging.getLogger(__name__)


def seed_forms(db: Session, filename_filter: Optional[str] = None):
    seeds_dir = os.path.join(os.path.dirname(__file__), "forms")
    if not os.path.exists(seeds_dir):
        logger.error("Seeds directory not found at %s", seeds_dir)
        return

    json_files = [
        f
        for f in os.listdir(seeds_dir)
        if f.endswith(".json") and f.startswith("form_")
    ]
    # Exclude form seeds with _vX suffix (e.g., _v2.json) by default
    # to avoid breaking general test cases.
    import re

    if not filename_filter:
        json_files = [
            f for f in json_files if not re.search(r"_v\d+\.json$", f)
        ]
    json_files.sort()

    for filename in json_files:
        if filename_filter and filename != filename_filter:
            logger.info("Skipping seed file due to filter: %s", filename)
            continue

        filepath = os.path.join(seeds_dir, filename)
        logger.info("Processing seed file: %s", filename)

        with open(filepath, "r") as file:
            form_data = json.load(file)

        form_name = form_data.get("name")
        if not form_name:
            logger.warning("Skipping %s: 'name' not found.", filename)
            continue

        # 1. Upsert Form
        form_id = form_data.get("form_id") or form_data.get("id")
        form = None
        if form_id:
            form = db.query(Form).filter(Form.id == form_id).first()
        if not form:
            form = db.query(Form).filter(Form.name.ilike(form_name)).first()

        if form:
            import sys

            should_replace = False
            # Check if running in pytest/tests to always overwrite
            is_testing = (
                "pytest" in sys.modules or os.getenv("TESTING") == "true"
            )
            if is_testing:
                should_replace = True
            elif sys.stdin.isatty():
                try:
                    prompt_msg = (
                        f"\nWarning: Form '{form_name}' (ID: {form.id}) "
                        "already exists in the database. Seeding will "
                        "OVERWRITE your edits. Do you want to replace it? (y/N): "  # noqa
                    )
                    user_input = input(prompt_msg)
                    if user_input.lower() in ["y", "yes"]:
                        should_replace = True
                except Exception:
                    pass

            if not should_replace:
                logger.info(
                    "Form '%s' already exists. Skipping to preserve edits.",
                    form_name,
                )
                continue

        languages = form_data.get("languages", ["en"])
        translations = form_data.get("translations", [])
        form_type = form_data.get("type", 1)
        if not form:
            form = Form(
                name=form_name,
                version=1,
                type=form_type,
                status=1,
                translations=translations,
                languages=languages,
            )
            db.add(form)
            db.flush()
            logger.info(
                "Created Form: %s (ID: %s, Type: %s)",
                form_name,
                form.id,
                form_type,
            )
        else:
            form.name = form_name
            form.translations = translations
            form.languages = languages
            form.type = form_type
            db.flush()
            logger.info(
                "Updated Form: %s (ID: %s, Type: %s)",
                form_name,
                form.id,
                form_type,
            )
        processed_group_ids = []
        processed_question_ids = []

        # 2. Iterate and Upsert Question Groups
        groups = form_data.get("question_group", [])
        for idx, group_data in enumerate(groups, start=1):
            group_name = group_data.get("name")
            order = group_data.get("order", idx)
            repeatable = group_data.get("repeatable", False)
            repeat_text = group_data.get("repeat_text")
            g_translations = group_data.get("translations", [])

            # Lookup group by form_id and group_name slug (case insensitive)
            q_group = (
                db.query(QuestionGroup)
                .filter(
                    QuestionGroup.form_id == form.id,
                    QuestionGroup.name.ilike(group_name),
                    QuestionGroup.deleted_at.is_(None),
                )
                .first()
            )

            if not q_group:
                q_group = QuestionGroup(
                    form_id=form.id,
                    name=group_name,
                    label=group_name,
                    translations=g_translations,
                    order=order,
                    repeatable=repeatable,
                    repeat_text=repeat_text,
                )
                db.add(q_group)
                db.flush()
                logger.info(
                    "  Created QuestionGroup: %s (ID: %s)",
                    group_name,
                    q_group.id,
                )
            else:
                q_group.order = order
                q_group.repeatable = repeatable
                q_group.repeat_text = repeat_text
                q_group.translations = g_translations
                db.flush()
                logger.info(
                    "  Updated/Verified QuestionGroup: %s (ID: %s)",
                    group_name,
                    q_group.id,
                )

            processed_group_ids.append(q_group.id)

            # 3. Iterate and Upsert Questions
            questions = group_data.get("question", [])
            for q_idx, q_data in enumerate(questions, start=1):
                q_pk = q_data.get("id")
                q_order = q_data.get("order", q_idx)
                q_type_str = q_data.get("type", "text")
                try:
                    q_type = QuestionType(q_type_str)
                except ValueError:
                    q_type = QuestionType.text
                q_required = q_data.get("required", True)
                q_translations = q_data.get("translations", [])

                # Schema-aware variable mapping
                if "label" in q_data:
                    # New schema style
                    q_name = q_data.get("name")
                    q_label = q_data.get("label") or q_name
                else:
                    # Old legacy schema style
                    q_name = str(
                        q_pk
                    )  # "id" contains the string slug (e.g. "incident_type")
                    q_label = (
                        q_data.get("label") or q_data.get("name") or q_name
                    )

                # Rule extraction
                rule = q_data.get("rule", {})

                # Extra config/API extraction
                api_config = None
                if q_type_str == "cascade":
                    api_config = q_data.get("api")
                    if isinstance(api_config, dict):
                        api_config = dict(api_config)
                    else:
                        api_config = {}

                    if "endpoint" in q_data and "endpoint" not in api_config:
                        api_config["endpoint"] = q_data.get("endpoint")
                    if "comment" in q_data and "comment" not in api_config:
                        api_config["comment"] = q_data.get("comment")

                # Lookup question by form_id and name slug (case-insensitive)
                q = None
                if q_name:
                    q = (
                        db.query(Question)
                        .filter(
                            Question.form_id == form.id,
                            Question.name.ilike(q_name),
                            Question.deleted_at.is_(None),
                        )
                        .first()
                    )

                if not q:
                    q = Question(
                        form_id=form.id,
                        question_group_id=q_group.id,
                        name=q_name,
                        label=q_label,
                        translations=q_translations,
                        order=q_order,
                        type=q_type,
                        required=q_required,
                        rule=rule if rule else None,
                        api=api_config,
                        extra=q_data.get("extra"),
                    )
                    db.add(q)
                    db.flush()
                    logger.info(
                        "    Created Question: %s (ID: %s)", q_name, q.id
                    )
                else:
                    q.question_group_id = q_group.id
                    q.name = q_name
                    q.label = q_label
                    q.order = q_order
                    q.type = q_type
                    q.required = q_required
                    q.rule = rule if rule else None
                    q.api = api_config
                    q.extra = q_data.get("extra")
                    q.translations = q_translations
                    q.deleted_at = None
                    db.flush()
                    logger.info(
                        "    Updated Question: %s (ID: %s)", q_name, q.id
                    )

                processed_question_ids.append(q.id)

                # 4. Recreate Options Freshly to avoid
                # unique/duplicate violations
                db.query(Option).filter(Option.question_id == q.id).delete(
                    synchronize_session=False
                )
                db.flush()

                options_data = q_data.get("option") or []
                for opt_idx, opt_data in enumerate(options_data, start=1):
                    opt_label = opt_data.get("name")
                    opt_val = str(opt_data.get("value"))
                    opt_order = opt_data.get("order", opt_idx)
                    opt_translations = opt_data.get("translations", [])

                    opt = Option(
                        question_id=q.id,
                        label=opt_label,
                        value=opt_val,
                        order=opt_order,
                        translations=opt_translations,
                    )
                    db.add(opt)
                    db.flush()
                    logger.info(
                        "      Created Option: %s -> %s (ID: %s)",
                        opt_val,
                        opt_label,
                        opt.id if hasattr(opt, "id") else "None",
                    )

        # 5. Soft-delete legacy question groups and questions
        # that are not present in the JSON seed

        if processed_question_ids:
            db.query(Question).filter(
                Question.form_id == form.id,
                Question.id.not_in(processed_question_ids),
                Question.deleted_at.is_(None),
            ).update(
                {Question.deleted_at: datetime.utcnow()},
                synchronize_session=False,
            )
            db.flush()

        if processed_group_ids:
            db.query(QuestionGroup).filter(
                QuestionGroup.form_id == form.id,
                QuestionGroup.id.not_in(processed_group_ids),
                QuestionGroup.deleted_at.is_(None),
            ).update(
                {QuestionGroup.deleted_at: datetime.utcnow()},
                synchronize_session=False,
            )
            db.flush()

        # 6. Publish Form to make it active and generate a schema snapshot
        publish_form_snapshot(form, db)

    logger.info("Database seeding successfully completed!")


if __name__ == "__main__":
    from app.database import SessionLocal
    import sys

    logging.basicConfig(level=logging.INFO)
    db_session = SessionLocal()
    try:
        # Check if a filename filter parameter is passed,
        # e.g. python form_seeder_helper.py form_v2.json
        filename_filter = sys.argv[1] if len(sys.argv) > 1 else None
        seed_forms(db_session, filename_filter=filename_filter)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close()
