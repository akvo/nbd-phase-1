import os
import json
import logging
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


def seed_forms(db: Session):
    seeds_dir = os.path.join(os.path.dirname(__file__), "forms")
    if not os.path.exists(seeds_dir):
        logger.error("Seeds directory not found at %s", seeds_dir)
        return

    json_files = [
        f
        for f in os.listdir(seeds_dir)
        if f.endswith(".json") and f.startswith("form_")
    ]
    json_files.sort()

    for filename in json_files:
        filepath = os.path.join(seeds_dir, filename)
        logger.info("Processing seed file: %s", filename)

        with open(filepath, "r") as file:
            form_data = json.load(file)

        form_name = form_data.get("name")
        if not form_name:
            logger.warning("Skipping %s: 'name' not found.", filename)
            continue

        # 1. Upsert Form
        form = db.query(Form).filter(Form.name == form_name).first()
        if not form:
            form = Form(name=form_name, version=1, type=1, status=1)
            db.add(form)
            db.flush()
            logger.info("Created Form: %s (ID: %s)", form_name, form.id)
        else:
            logger.info("Form already exists: %s (ID: %s)", form_name, form.id)

        # 2. Iterate and Upsert Question Groups
        groups = form_data.get("question_group", [])
        for idx, group_data in enumerate(groups, start=1):
            group_name = group_data.get("name")
            order = group_data.get("order", idx)
            repeatable = group_data.get("repeatable", False)
            repeat_text = group_data.get("repeat_text")

            q_group = (
                db.query(QuestionGroup)
                .filter(
                    QuestionGroup.form_id == form.id,
                    QuestionGroup.name == group_name,
                    QuestionGroup.deleted_at.is_(None),
                )
                .first()
            )

            if not q_group:
                q_group = QuestionGroup(
                    form_id=form.id,
                    name=group_name,
                    label=group_name,
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
                db.flush()
                logger.info(
                    "  Updated/Verified QuestionGroup: %s (ID: %s)",
                    group_name,
                    q_group.id,
                )

            # 3. Iterate and Upsert Questions
            questions = group_data.get("question", [])
            for q_idx, q_data in enumerate(questions, start=1):
                q_id = q_data.get("id")
                q_order = q_data.get("order", q_idx)
                q_type_str = q_data.get("type", "text")
                try:
                    q_type = QuestionType(q_type_str)
                except ValueError:
                    q_type = QuestionType.text
                q_label = q_data.get("name", q_id)
                q_required = q_data.get("required", True)

                # Rule extraction
                rule = q_data.get("rule", {})

                # Extra config/API extraction
                api_config = None
                if q_type_str == "cascade":
                    api_config = {
                        "endpoint": q_data.get("endpoint"),
                        "comment": q_data.get("comment"),
                    }

                q = (
                    db.query(Question)
                    .filter(
                        Question.form_id == form.id,
                        Question.name == q_id,
                        Question.deleted_at.is_(None),
                    )
                    .first()
                )

                if not q:
                    q = Question(
                        form_id=form.id,
                        question_group_id=q_group.id,
                        name=q_id,
                        label=q_label,
                        order=q_order,
                        type=q_type,
                        required=q_required,
                        rule=rule if rule else None,
                        api=api_config,
                    )
                    db.add(q)
                    db.flush()
                    logger.info(
                        "    Created Question: %s (ID: %s)", q_id, q.id
                    )
                else:
                    q.label = q_label
                    q.order = q_order
                    q.type = q_type
                    q.required = q_required
                    q.rule = rule if rule else None
                    q.api = api_config
                    db.flush()
                    logger.info(
                        "    Updated Question: %s (ID: %s)", q_id, q.id
                    )

                # 4. Iterate and Upsert Options
                options_data = q_data.get("option", [])
                for opt_idx, opt_data in enumerate(options_data, start=1):
                    opt_label = opt_data.get("name")
                    opt_val = str(opt_data.get("value"))
                    opt_order = opt_data.get("order", opt_idx)

                    opt = (
                        db.query(Option)
                        .filter(
                            Option.question_id == q.id, Option.value == opt_val
                        )
                        .first()
                    )

                    if not opt:
                        opt = Option(
                            question_id=q.id,
                            label=opt_label,
                            value=opt_val,
                            order=opt_order,
                        )
                        db.add(opt)
                        db.flush()
                        logger.info(
                            "      Created Option: %s -> %s",
                            opt_val,
                            opt_label,
                        )
                    else:
                        opt.label = opt_label
                        opt.order = opt_order
                        db.flush()
                        logger.info(
                            "      Updated Option: %s -> %s",
                            opt_val,
                            opt_label,
                        )

        # 5. Publish Form to make it active and generate a schema snapshot
        publish_form_snapshot(form, db)

    db.commit()
    logger.info("Database seeding successfully completed!")
