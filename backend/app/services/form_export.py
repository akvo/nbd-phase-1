import io
import csv
from sqlalchemy.orm import Session
from openpyxl import Workbook
from typing import Dict, Any

from app.models.form import Form, FormPublishedVersion, QuestionGroup
from app.models.spatial import Basin, Wetland, Site, SpatialBoundary
from app.schemas.form import FormBlueprintResponse


class FormExportService:
    @staticmethod
    def generate_blueprint_json(
        db: Session, form_id: int, draft: bool = False
    ) -> Dict[str, Any]:
        db_form = db.query(Form).filter(Form.id == form_id).first()
        if not db_form:
            raise ValueError("Form not found")

        # Try to use published version unless draft=True is requested
        if not draft and db_form.active_version_id:
            pub_version = (
                db.query(FormPublishedVersion)
                .filter(FormPublishedVersion.id == db_form.active_version_id)
                .first()
            )
            if pub_version and pub_version.schema:
                # Return the pre-saved schema dict directly
                return pub_version.schema

        # Fallback to live relational database tables
        active_groups = (
            db.query(QuestionGroup)
            .filter(
                QuestionGroup.form_id == form_id,
                QuestionGroup.deleted_at.is_(None),
            )
            .order_by(QuestionGroup.order.asc().nullslast())
            .all()
        )
        response_obj = FormBlueprintResponse.from_orm_model(
            db_form, active_groups
        )
        return response_obj.model_dump()

    @staticmethod
    def get_translation_label(
        item: Dict[str, Any], lang: str, default_val: str
    ) -> str:
        translations = item.get("translations") or []
        for trans in translations:
            t_lang = trans.get("lang") or trans.get("language")
            if t_lang == lang:
                val = (
                    trans.get("label")
                    or trans.get("name")
                    or trans.get("description")
                )
                if val:
                    return val
        if lang == "en":
            val = (
                item.get("label")
                or item.get("name")
                or item.get("description")
            )
            if val:
                return val
        return default_val

    @classmethod
    def generate_xlsform(
        cls, db: Session, form_id: int, draft: bool = False
    ) -> io.BytesIO:
        blueprint = cls.generate_blueprint_json(db, form_id, draft)

        wb = Workbook()
        # openpyxl starts with a default active sheet, rename it to 'survey'
        survey_sheet = wb.active
        survey_sheet.title = "survey"
        choices_sheet = wb.create_sheet(title="choices")
        settings_sheet = wb.create_sheet(title="settings")

        # Map language codes to Kobo standard label syntax
        language_map = {
            "en": "English (en)",
            "sw": "Swahili (sw)",
            "fr": "French (fr)",
            "es": "Spanish (es)",
        }

        # Resolve languages dynamically
        languages = blueprint.get("languages") or ["en"]
        default_lang_code = blueprint.get("defaultLanguage") or "en"
        default_lang_name = language_map.get(
            default_lang_code,
            f"{default_lang_code.upper()} ({default_lang_code})",
        )

        # 1. Write settings sheet
        settings_headers = [
            "form_title",
            "form_id",
            "version",
            "default_language",
        ]
        settings_sheet.append(settings_headers)
        settings_sheet.append(
            [
                blueprint.get("name", "Form"),
                blueprint.get("name", "Form").lower().replace(" ", "_"),
                str(blueprint.get("version", 1)),
                default_lang_name,
            ]
        )

        # 2. Write survey and choices sheets
        survey_headers = ["type", "name"]
        for lang in languages:
            lang_name = language_map.get(lang, f"{lang.upper()} ({lang})")
            survey_headers.append(f"label::{lang_name}")
        survey_headers.extend(["required", "hint", "relevant"])
        survey_sheet.append(survey_headers)

        choices_headers = ["list_name", "name"]
        for lang in languages:
            lang_name = language_map.get(lang, f"{lang.upper()} ({lang})")
            choices_headers.append(f"label::{lang_name}")
        choices_sheet.append(choices_headers)

        question_groups = blueprint.get("question_group", [])
        for group in question_groups:
            # Write group start
            group_name = group.get("name")

            # Map group labels dynamically
            group_labels = []
            for lang in languages:
                lbl = cls.get_translation_label(
                    group,
                    lang,
                    group.get("label") or group.get("description", ""),
                )
                group_labels.append(lbl)

            row = ["begin_group", group_name]
            row.extend(group_labels)
            row.extend(["", "", ""])
            survey_sheet.append(row)

            questions = group.get("question", [])
            for q in questions:
                q_name = q.get("name")
                q_type = q.get("type", "text")
                required_val = "yes" if q.get("required") else "no"
                hint_val = (
                    q.get("tooltip", {}).get("text", "")
                    if isinstance(q.get("tooltip"), dict)
                    else ""
                )

                # Map question labels dynamically
                q_labels = []
                for lang in languages:
                    lbl = cls.get_translation_label(
                        q, lang, q.get("label", "")
                    )
                    q_labels.append(lbl)

                # Dependencies mapping (relevancy rules)
                relevant_val = ""
                deps = q.get("dependency", [])
                if deps:
                    rules = []
                    for dep in deps:
                        dep_q = dep.get("question")
                        dep_val = dep.get("value")
                        if dep_q and dep_val is not None:
                            rules.append(f"${{{dep_q}}} = '{dep_val}'")
                    op = (
                        " and " if q.get("dependencyRule") == "AND" else " or "
                    )
                    relevant_val = op.join(rules)

                # Map type to Kobo standard
                xls_type = "text"
                is_cascade = False

                if q_type == "integer":
                    xls_type = "integer"
                elif q_type == "decimal" or q_type == "number":
                    xls_type = "decimal"
                elif q_type == "date":
                    xls_type = "date"
                elif q_type == "image" or q_type == "photo":
                    xls_type = "image"
                elif q_type == "geopoint" or q_type == "gps":
                    xls_type = "geopoint"
                elif q_type in ("select_one", "select_multiple", "option"):
                    # Check if it uses external file for cascade
                    q_extra = q.get("extra") or {}
                    if (
                        q_extra.get("cascade")
                        or "cascade" in q_name.lower()
                        or q_name
                        in (
                            "site_id",
                            "wetland_id",
                            "basin_id",
                            "subcounty_id",
                            "location_id",
                        )
                    ):
                        xls_type = "select_one_from_file spatial_cascade.csv"
                        is_cascade = True
                    else:
                        prefix_val = (
                            "select_multiple"
                            if q_type == "select_multiple"
                            else "select_one"
                        )
                        xls_type = f"{prefix_val} option_{q_name}"

                q_row = [xls_type, q_name]
                q_row.extend(q_labels)
                q_row.extend([required_val, hint_val, relevant_val])
                survey_sheet.append(q_row)

                # Populate choices if multiple choice and not external cascade
                if (
                    q_type in ("select_one", "select_multiple", "option")
                    and not is_cascade
                ):
                    options = q.get("option") or []
                    if isinstance(options, str):
                        options = []
                    for opt in options:
                        opt_name = opt.get("value") or opt.get("name")

                        opt_labels = []
                        for lang in languages:
                            lbl = cls.get_translation_label(
                                opt,
                                lang,
                                opt.get("label") or opt.get("name") or "",
                            )
                            opt_labels.append(lbl)

                        opt_row = [f"option_{q_name}", opt_name]
                        opt_row.extend(opt_labels)
                        choices_sheet.append(opt_row)

            # Write group end
            end_row = ["end_group", ""]
            end_row.extend(["" for _ in languages])
            end_row.extend(["", "", ""])
            survey_sheet.append(end_row)

        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        return file_stream

    @staticmethod
    def generate_spatial_cascade_csv(db: Session) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["list_name", "name", "label", "parent_key"])

        # 1. Export Basins
        basins = db.query(Basin).order_by(Basin.name).all()
        for b in basins:
            writer.writerow(["basin", str(b.id), b.name, ""])

        # 2. Export Spatial Boundaries
        # (Regions, Districts/Counties, Sub-counties)
        boundaries = (
            db.query(SpatialBoundary)
            .order_by(SpatialBoundary.level, SpatialBoundary.name)
            .all()
        )
        for s in boundaries:
            list_name = "subcounty"
            if s.level == 1:
                list_name = "region"
            elif s.level == 2:
                list_name = "district"

            parent_key = str(s.parent_id) if s.parent_id else ""
            writer.writerow([list_name, str(s.id), s.name, parent_key])

        # 3. Export Wetlands
        wetlands = db.query(Wetland).order_by(Wetland.name).all()
        for w in wetlands:
            writer.writerow(["wetland", str(w.id), w.name, str(w.basin_id)])

        # 4. Export Sites
        sites = db.query(Site).order_by(Site.name).all()
        for s in sites:
            writer.writerow(["site", str(s.id), s.name, str(s.wetland_id)])

        output.seek(0)
        return output
