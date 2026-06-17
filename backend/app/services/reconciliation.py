import os
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.submission import Datapoint, Answer
from app.models.sampling_record import SamplingRecord
from app.models.citizen import Citizen
from app.models.reconciliation import ReconciliationLog


def reconcile_lab_datapoint(db: Session, lab_dp_id: int) -> None:
    """
    Automatically compares a newly approved Lab QA datapoint
    against citizen scientists' field readings (sampling records)
    at the same site within a 90-day window.
    """
    lab_dp = db.query(Datapoint).filter(Datapoint.id == lab_dp_id).first()
    if not lab_dp or lab_dp.site_id is None:
        return

    # 1. Fetch and map all approved Lab QA answers
    answers = db.query(Answer).filter(Answer.datapoint_id == lab_dp_id).all()
    lab_ph = None
    lab_temp = None
    lab_do = None

    for ans in answers:
        if not ans.question:
            continue
        q_name = (ans.question.name or "").lower()
        q_label = (ans.question.label or "").lower()

        if "ph" in q_name or "ph" in q_label:
            if ans.value is not None:
                lab_ph = Decimal(str(ans.value))
        elif "temp" in q_name or "temperature" in q_label:
            if ans.value is not None:
                lab_temp = Decimal(str(ans.value))
        elif (
            "do" in q_name
            or "dissolved" in q_name
            or "oxygen" in q_name
            or "dissolved oxygen" in q_label
        ):
            if ans.value is not None:
                lab_do = Decimal(str(ans.value))

    # If all parameter answers are missing, nothing to compare
    if lab_ph is None and lab_temp is None and lab_do is None:
        return

    # 2. Query citizen scientist sampling records within 90 days window
    start_date = lab_dp.created_at - timedelta(days=90)
    end_date = lab_dp.created_at + timedelta(days=90)

    citizen_records = (
        db.query(SamplingRecord)
        .filter(
            SamplingRecord.site_id == lab_dp.site_id,
            SamplingRecord.sampled_at >= start_date,
            SamplingRecord.sampled_at <= end_date,
        )
        .all()
    )

    if not citizen_records:
        return

    # 3. Find citizens registered at this site
    citizens = (
        db.query(Citizen).filter(Citizen.site_id == lab_dp.site_id).all()
    )
    if not citizens:
        return

    # 4. Compare parameters and log results
    threshold = Decimal(os.getenv("RECONCILIATION_VARIANCE_THRESHOLD", "20.0"))

    for record in citizen_records:
        comparisons = [
            ("ph_value", record.ph_value, lab_ph),
            ("temp_value", record.temp_value, lab_temp),
            ("do_value", record.do_value, lab_do),
        ]

        for param_name, citizen_val, lab_val in comparisons:
            if citizen_val is None or lab_val is None:
                continue
            if lab_val == Decimal("0"):
                continue

            citizen_dec = Decimal(str(citizen_val))
            lab_dec = Decimal(str(lab_val))

            # Calculate percentage variance
            variance = (abs(citizen_dec - lab_dec) / lab_dec) * Decimal("100")
            status = (
                "DISCREPANT" if variance > threshold else "RECONCILIATION_OK"
            )

            for citizen in citizens:
                # Enforce idempotency by checking for existing log
                existing = (
                    db.query(ReconciliationLog)
                    .filter(
                        ReconciliationLog.citizen_id == citizen.id,
                        ReconciliationLog.citizen_datapoint_id == record.id,
                        ReconciliationLog.lab_datapoint_id == lab_dp.id,
                        ReconciliationLog.parameter_name == param_name,
                    )
                    .first()
                )

                if existing:
                    existing.citizen_value = citizen_dec
                    existing.lab_value = lab_dec
                    existing.calculated_variance = variance
                    existing.status = status
                    existing.reconciled_at = datetime.utcnow()
                else:
                    new_log = ReconciliationLog(
                        citizen_id=citizen.id,
                        citizen_datapoint_id=record.id,
                        lab_datapoint_id=lab_dp.id,
                        parameter_name=param_name,
                        citizen_value=citizen_dec,
                        lab_value=lab_dec,
                        calculated_variance=variance,
                        status=status,
                    )
                    db.add(new_log)
    db.commit()
