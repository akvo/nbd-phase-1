from decimal import Decimal


def calculate_wqi_and_scores(
    ph: Decimal,
    do: Decimal,
    water_level: str,
    invasive_macrophytes: Decimal,
) -> dict:
    """Calculates WQI parameters and aggregates group scores."""
    # 1. WQI calculations
    s_ph = Decimal("8.5")
    s_do = Decimal("5.0")

    v_io_ph = Decimal("7.0")
    v_io_do = Decimal("14.6")

    # K = 1 / (1/8.5 + 1/5.0)
    k = Decimal("1") / (Decimal("1") / s_ph + Decimal("1") / s_do)

    # Unit weights
    w_ph = k / s_ph
    w_do = k / s_do

    # Quality ratings (q_n)
    q_ph = Decimal("100") * (ph - v_io_ph) / (s_ph - v_io_ph)
    q_do = Decimal("100") * (do - v_io_do) / (s_do - v_io_do)

    # Total WQI
    wqi = w_ph * q_ph + w_do * q_do

    # Physico-chemical Score
    physico_chemical_score = Decimal("1.0") - wqi / Decimal("100")
    physico_chemical_score = max(
        Decimal("0.00"), min(Decimal("1.00"), physico_chemical_score)
    )
    physico_chemical_score = physico_chemical_score.quantize(Decimal("0.01"))

    # 2. Catchment score
    wl = str(water_level).upper().strip()
    if wl == "MEDIUM":
        catchment_score = Decimal("1.00")
    elif wl == "HIGH":
        catchment_score = Decimal("0.60")
    elif wl == "LOW":
        catchment_score = Decimal("0.30")
    else:
        catchment_score = Decimal("1.00")

    # 3. Ecological score
    eco_score = Decimal("1.0") - (invasive_macrophytes / Decimal("100.0"))
    ecological_score = max(Decimal("0.00"), min(Decimal("1.00"), eco_score))
    ecological_score = ecological_score.quantize(Decimal("0.01"))

    # 4. Composite score
    composite = (
        physico_chemical_score + catchment_score + ecological_score
    ) / Decimal("3.0")
    composite_score = composite.quantize(Decimal("0.01"))

    # 5. Health class mapping
    if composite_score >= Decimal("0.80"):
        health_class = "A"
    elif composite_score >= Decimal("0.60"):
        health_class = "B"
    elif composite_score >= Decimal("0.40"):
        health_class = "C"
    elif composite_score >= Decimal("0.20"):
        health_class = "D"
    else:
        health_class = "E"

    return {
        "wqi_score": physico_chemical_score,
        "catchment_score": catchment_score,
        "ecological_score": ecological_score,
        "composite_score": composite_score,
        "health_class": health_class,
    }
