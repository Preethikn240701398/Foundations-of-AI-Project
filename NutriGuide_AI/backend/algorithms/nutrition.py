"""
Step 2 of the implementation pipeline - BMI and basic nutritional requirement calculation.

Pure functions only (no FastAPI / MongoDB imports) so the maths can be unit-tested
and explained line by line in the viva.

Formulae used
-------------
BMI   = weight_kg / height_m^2                       (WHO categories)
BMR   = Mifflin-St Jeor equation                      (most accurate for healthy adults)
TDEE  = BMR x activity multiplier                     (maintenance calories)
Target = TDEE adjusted for the goal, pregnancy/lactation and a safety floor
Macros = protein by g/kg, fat by % of kcal, carbohydrate = remainder
"""
from __future__ import annotations

ACTIVITY_LEVELS: dict[str, dict] = {
    "sedentary": {"multiplier": 1.2, "label": "Sedentary", "hint": "Desk job, little or no exercise"},
    "light": {"multiplier": 1.375, "label": "Lightly active", "hint": "Exercise 1-3 days a week"},
    "moderate": {"multiplier": 1.55, "label": "Moderately active", "hint": "Exercise 3-5 days a week"},
    "active": {"multiplier": 1.725, "label": "Very active", "hint": "Hard exercise 6-7 days a week"},
    "athlete": {"multiplier": 1.9, "label": "Athlete", "hint": "Twice-daily training or a physical job"},
}

GOALS: dict[str, dict] = {
    "weight_loss": {"label": "Lose weight", "kcal_pct": -0.20, "protein_per_kg": 1.8, "fat_pct": 0.27},
    "balanced": {"label": "Stay balanced", "kcal_pct": 0.0, "protein_per_kg": 1.2, "fat_pct": 0.30},
    "muscle_gain": {"label": "Build muscle", "kcal_pct": 0.12, "protein_per_kg": 2.0, "fat_pct": 0.25},
    "weight_gain": {"label": "Gain weight", "kcal_pct": 0.15, "protein_per_kg": 1.6, "fat_pct": 0.28},
}

GOAL_ALIASES = {
    "muscle": "muscle_gain",
    "maintain": "balanced",
    "maintenance": "balanced",
    "lose_weight": "weight_loss",
    "gain_weight": "weight_gain",
    "fat_loss": "weight_loss",
}

BMI_BANDS = [
    (18.5, "underweight", "Underweight"),
    (25.0, "normal", "Healthy weight"),
    (30.0, "overweight", "Overweight"),
    (float("inf"), "obese", "Obesity range"),
]


def normalize_goal(goal: str | None) -> str:
    g = str(goal or "balanced").strip().lower().replace(" ", "_").replace("-", "_")
    g = GOAL_ALIASES.get(g, g)
    return g if g in GOALS else "balanced"


def normalize_activity(level: str | None) -> str:
    a = str(level or "light").strip().lower()
    return a if a in ACTIVITY_LEVELS else "light"


def bmi_value(weight_kg: float, height_cm: float) -> float:
    h = max(float(height_cm), 1.0) / 100.0
    return round(float(weight_kg) / (h * h), 1)


def bmi_category(bmi: float) -> tuple[str, str]:
    for upper, key, label in BMI_BANDS:
        if bmi < upper:
            return key, label
    return "obese", "Obesity range"


def healthy_weight_range(height_cm: float) -> tuple[float, float]:
    h = float(height_cm) / 100.0
    return round(18.5 * h * h, 1), round(24.9 * h * h, 1)


def bmr_mifflin(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    sex = (sex or "").lower()
    if sex.startswith("m"):
        return base + 5
    if sex.startswith("f"):
        return base - 161
    return base - 78  # midpoint when sex is not specified


def compute_requirements(profile: dict) -> dict:
    """Return the full set of daily targets together with a human-readable derivation."""
    weight = float(profile.get("weight") or 70)
    height = float(profile.get("height_cm") or 170)
    age = int(profile.get("age") or 25)
    sex = str(profile.get("sex") or "other")
    activity = normalize_activity(profile.get("activity_level"))
    goal = normalize_goal(profile.get("goal"))
    stage = str(profile.get("life_stage") or "adult").lower()
    conditions = _conditions(profile)

    steps: list[str] = []
    warnings: list[str] = []

    bmi = bmi_value(weight, height)
    cat_key, cat_label = bmi_category(bmi)
    lo, hi = healthy_weight_range(height)
    steps.append(f"BMI = {weight:g} kg / ({height / 100:.2f} m)^2 = {bmi}  ->  {cat_label}")

    bmr = bmr_mifflin(weight, height, age, sex)
    steps.append(f"BMR (Mifflin-St Jeor) = 10x{weight:g} + 6.25x{height:g} - 5x{age} "
                 f"{'+ 5' if sex.lower().startswith('m') else '- 161' if sex.lower().startswith('f') else '- 78'} = {bmr:.0f} kcal")

    mult = ACTIVITY_LEVELS[activity]["multiplier"]
    tdee = bmr * mult
    steps.append(f"TDEE = BMR x {mult} ({ACTIVITY_LEVELS[activity]['label']}) = {tdee:.0f} kcal")

    # --- goal safety rules -------------------------------------------------
    effective_goal = goal
    if goal == "weight_loss" and cat_key == "underweight":
        effective_goal = "balanced"
        warnings.append("Your BMI is in the underweight range, so a weight-loss target is not recommended. "
                        "Maintenance calories are used instead.")
    if goal in {"weight_gain", "muscle_gain"} and cat_key == "obese":
        warnings.append("Your BMI is in the obesity range. Consider speaking with a clinician before a calorie surplus.")

    g = GOALS[effective_goal]
    delta = tdee * g["kcal_pct"]
    if delta < -750:
        delta = -750  # never recommend more than ~0.7 kg/week loss
    calories = tdee + delta
    if delta:
        steps.append(f"Goal adjustment ({g['label']}) = {delta:+.0f} kcal")

    if stage == "pregnancy":
        calories += 300
        steps.append("Pregnancy allowance = +300 kcal")
    elif stage == "lactation":
        calories += 450
        steps.append("Lactation allowance = +450 kcal")

    floor = 1500 if sex.lower().startswith("m") else 1200
    if calories < floor:
        warnings.append(f"Calculated target was below the safe minimum, raised to {floor} kcal.")
        calories = floor
        steps.append(f"Safety floor applied: {floor} kcal")
    calories = int(round(calories / 10.0) * 10)
    steps.append(f"Daily calorie target = {calories} kcal")

    # --- macros -------------------------------------------------------------
    # use an adjusted reference weight when BMI >= 25 so protein is not over-estimated
    ref_weight = weight if bmi < 25 else lo_hi_ref(weight, hi)
    protein_g = g["protein_per_kg"] * ref_weight
    protein_g = min(max(protein_g, 0.10 * calories / 4), 0.35 * calories / 4)
    if stage == "pregnancy":
        protein_g = max(protein_g, 1.1 * ref_weight)
    fat_pct = g["fat_pct"]
    carb_cap = 0.45 if conditions & {"diabetes", "prediabetes", "pcos"} else 1.0
    fat_g = fat_pct * calories / 9
    carbs_g = (calories - protein_g * 4 - fat_g * 9) / 4
    if carbs_g * 4 > carb_cap * calories:  # shift energy from carbs to fat for glycaemic control
        carbs_g = carb_cap * calories / 4
        fat_g = (calories - protein_g * 4 - carbs_g * 4) / 9
        steps.append("Carbohydrate share capped at 45% for glycaemic control")
    carbs_g = max(carbs_g, 0.0)

    fiber_g = max(25, round(14 * calories / 1000))
    water_ml = int(round(weight * 35 / 50.0) * 50) + (700 if stage in {"pregnancy", "lactation"} else 0)
    sodium_limit = 1500 if "hypertension" in conditions else 2300
    gi_max = int(profile.get("glycemic_target_max") or 55)
    if conditions & {"diabetes", "prediabetes", "pcos"}:
        gi_max = min(gi_max, 55)

    protein_g, carbs_g, fat_g = round(protein_g), round(carbs_g), round(fat_g)
    steps.append(f"Protein {protein_g} g  |  Carbs {carbs_g} g  |  Fat {fat_g} g  |  Fibre {fiber_g} g")

    kcal_from = {"protein": protein_g * 4, "carbs": carbs_g * 4, "fat": fat_g * 9}
    total = max(sum(kcal_from.values()), 1)
    macro_pct = {k: round(v / total * 100) for k, v in kcal_from.items()}

    # weight-change estimate (7700 kcal ~ 1 kg)
    weekly_change_kg = round((calories - tdee) * 7 / 7700, 2) if stage == "adult" else None

    return {
        "bmi": bmi,
        "bmi_category": cat_key,
        "bmi_label": cat_label,
        "healthy_weight_min": lo,
        "healthy_weight_max": hi,
        "bmr": round(bmr),
        "activity_multiplier": mult,
        "tdee": round(tdee),
        "goal": effective_goal,
        "requested_goal": goal,
        "calories": calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "fiber_g": fiber_g,
        "water_ml": water_ml,
        "sodium_limit_mg": sodium_limit,
        "glycemic_max": gi_max,
        "macro_pct": macro_pct,
        "weekly_change_kg": weekly_change_kg,
        "steps": steps,
        "warnings": warnings,
    }


def lo_hi_ref(weight: float, healthy_max: float) -> float:
    return healthy_max + 0.25 * max(weight - healthy_max, 0.0)


def _conditions(profile: dict) -> set[str]:
    raw = profile.get("health_condition") or "none"
    if isinstance(raw, (list, tuple, set)):
        items = raw
    else:
        items = str(raw).replace(";", ",").split(",")
    out = {str(c).strip().lower().replace(" ", "_") for c in items}
    return {c for c in out if c and c not in {"none", "healthy"}}


def conditions_of(profile: dict) -> set[str]:
    return _conditions(profile)


def apply_targets(profile: dict) -> dict:
    """Return profile fields that must be refreshed whenever body data changes."""
    req = compute_requirements(profile)
    return {
        "daily_calories_target": req["calories"],
        "protein_target": req["protein_g"],
        "carbs_target": req["carbs_g"],
        "fat_target": req["fat_g"],
        "fiber_target": req["fiber_g"],
        "glycemic_target_max": req["glycemic_max"],
        "bmi": req["bmi"],
    }
