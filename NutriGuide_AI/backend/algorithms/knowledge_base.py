"""
Steps 3 and 4 of the implementation pipeline - Knowledge base creation and rule definition.

The knowledge base has three layers
1. Ontology    - vocabulary: allergens, diets, medical conditions, food properties
2. Thresholds  - how raw numbers (GI, protein, sodium ...) become symbolic food properties
3. Rules       - IF-THEN production rules written as readable strings, e.g.
                 "allergy(?a) AND contains(?a)  ->  reject"

Rules are DATA, not code: the inference engine (logic.py) simply loads this list, so a
nutritionist could add or edit rules without touching any Python logic.
Variables start with '?' and are unified with facts (a small piece of first-order logic).
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 1. ONTOLOGY
# ---------------------------------------------------------------------------
ALLERGENS = ["peanut", "nuts", "dairy", "gluten", "egg", "soy", "fish", "shellfish", "sesame"]

ALLERGEN_SYNONYMS = {
    "peanuts": "peanut", "groundnut": "peanut", "groundnuts": "peanut",
    "tree nut": "nuts", "tree nuts": "nuts", "nut": "nuts", "almond": "nuts", "cashew": "nuts",
    "milk": "dairy", "lactose": "dairy", "cheese": "dairy",
    "wheat": "gluten", "barley": "gluten",
    "eggs": "egg",
    "soya": "soy", "soybean": "soy",
    "prawn": "shellfish", "prawns": "shellfish", "shrimp": "shellfish", "crab": "shellfish",
    "seafood": "shellfish", "sesame seeds": "sesame",
}

DIETS = {
    "vegetarian": "No meat or fish. Eggs and dairy allowed.",
    "vegan": "No animal products at all.",
    "eggetarian": "Vegetarian plus eggs. No meat or fish.",
    "pescatarian": "No meat. Fish and seafood allowed.",
}

CONDITIONS = {
    "diabetes": {
        "label": "Type 2 diabetes",
        "summary": "Keep glycaemic index low and spread carbohydrates evenly.",
        "guidelines": ["Glycaemic index at or below 55", "Prefer fibre-rich whole grains and legumes",
                       "Avoid sugary drinks and refined flour"],
    },
    "prediabetes": {
        "label": "Prediabetes",
        "summary": "Favour low-GI foods to improve insulin sensitivity.",
        "guidelines": ["Prefer low-GI carbohydrates", "Add fibre at every meal", "Limit sweets"],
    },
    "pcos": {
        "label": "PCOS",
        "summary": "Low-GI, high-fibre eating supports hormonal balance.",
        "guidelines": ["Prefer low-GI carbohydrates", "Include lean protein", "Limit refined sugar"],
    },
    "hypertension": {
        "label": "Hypertension",
        "summary": "Limit sodium to about 1500 mg per day.",
        "guidelines": ["Sodium under 1500 mg per day", "Avoid pickles, processed and fried food",
                       "Prefer potassium-rich vegetables"],
    },
    "high_cholesterol": {
        "label": "High cholesterol",
        "summary": "Increase soluble fibre and avoid deep-fried foods.",
        "guidelines": ["Avoid fried food", "Prefer oats, legumes, nuts and fish", "Limit full-fat dairy"],
    },
    "anemia": {
        "label": "Iron-deficiency anaemia",
        "summary": "Choose iron-rich foods paired with vitamin C.",
        "guidelines": ["Prefer iron-rich foods (greens, legumes, red meat)", "Pair with vitamin-C fruit",
                       "Avoid tea/coffee with meals"],
    },
}

LIFE_STAGES = {
    "adult": "Adult (18-59)",
    "teen": "Teen (13-17)",
    "senior": "Senior (60+)",
    "pregnancy": "Pregnancy",
    "lactation": "Breastfeeding",
}

# ---------------------------------------------------------------------------
# 2. THRESHOLDS  (numbers -> symbolic properties)
# ---------------------------------------------------------------------------
THRESHOLDS = {
    "high_gi": "glycaemic index > your personal limit (default 55)",
    "low_gi": "glycaemic index <= 45",
    "high_protein": "protein >= 20 g per serving",
    "high_fiber": "fibre >= 6 g per serving",
    "calorie_dense": "energy >= 600 kcal per serving",
    "light": "energy <= 300 kcal per serving",
    "high_sodium": "sodium >= 800 mg per serving",
    "low_sodium": "sodium <= 300 mg per serving",
    "high_sugar": "tagged sweet / dessert",
    "fried": "tagged fried",
}

MEAT_TAGS = {"meat", "chicken", "beef", "mutton", "lamb", "pork", "turkey"}
FISH_TAGS = {"fish", "shellfish"}
ANIMAL_TAGS = MEAT_TAGS | FISH_TAGS | {"egg", "dairy", "paneer", "honey", "ghee"}


def normalize_allergen(value: str) -> str:
    v = str(value or "").strip().lower()
    return ALLERGEN_SYNONYMS.get(v, v)


def item_properties(item: dict, profile: dict | None = None) -> set[str]:
    """Derive symbolic properties for a meal/food from its numbers and tags."""
    profile = profile or {}
    tags = {str(t).lower() for t in item.get("tags") or []}
    allergens = {normalize_allergen(a) for a in item.get("allergens") or []}
    props: set[str] = set()

    gi = item.get("glycemic_index")
    gi_max = int(profile.get("glycemic_target_max") or 55)
    if gi is not None:
        gi = int(gi)
        if gi > gi_max:
            props.add("high_gi")
        if gi <= 45:
            props.add("low_gi")

    kcal = float(item.get("calories") or 0)
    protein = float(item.get("protein") or 0)
    fiber = float(item.get("fiber") or 0)
    sodium = item.get("sodium_mg")

    if protein >= 20:
        props.add("high_protein")
    if fiber >= 6 or "fiber" in tags:
        props.add("high_fiber")
    if kcal >= 600:
        props.add("calorie_dense")
    if 0 < kcal <= 300:
        props.add("light")
    if sodium is not None:
        if float(sodium) >= 800:
            props.add("high_sodium")
        if float(sodium) <= 300:
            props.add("low_sodium")
    if tags & {"sweet", "dessert"}:
        props.add("high_sugar")
    if "fried" in tags:
        props.add("fried")
    if tags & {"iron", "iron_rich"} or ("leafy" in tags and "legume" in tags):
        props.add("iron_rich")
    if tags & {"folate", "leafy", "legume"}:
        props.add("folate_rich")
    if tags & {"raw_fish", "alcohol", "unpasteurized"}:
        props.add("unsafe_pregnancy")
    if tags & ANIMAL_TAGS or allergens & {"dairy", "egg", "fish", "shellfish"}:
        props.add("animal_product")
    if tags & MEAT_TAGS:
        props.add("meat")
    if tags & FISH_TAGS or "fish" in allergens or "shellfish" in allergens:
        props.add("fish")
    if "egg" in tags or "egg" in allergens:
        props.add("egg")
    return props


def item_contains(item: dict) -> set[str]:
    tags = {normalize_allergen(t) for t in item.get("tags") or []}
    allergens = {normalize_allergen(a) for a in item.get("allergens") or []}
    return (tags | allergens) & set(ALLERGENS)


# ---------------------------------------------------------------------------
# 3. RULES
# ---------------------------------------------------------------------------
# type   : derive  -> adds a new fact (intermediate reasoning step)
#          reject  -> hard exclusion (safety)
#          caution -> soft penalty
#          prefer  -> soft bonus
# weight : points added to / removed from the item's score
RULES: list[dict] = [
    # ---- derive needs (level 1 reasoning) --------------------------------
    {"id": "N01", "cat": "need", "if": "condition(diabetes)", "then": "need(low_gi)", "type": "derive",
     "text": "Diabetes means you need low-glycaemic foods."},
    {"id": "N02", "cat": "need", "if": "condition(prediabetes)", "then": "need(low_gi)", "type": "derive",
     "text": "Prediabetes means you need low-glycaemic foods."},
    {"id": "N03", "cat": "need", "if": "condition(pcos)", "then": "need(low_gi)", "type": "derive",
     "text": "PCOS benefits from low-glycaemic foods."},
    {"id": "N04", "cat": "need", "if": "condition(hypertension)", "then": "need(low_sodium)", "type": "derive",
     "text": "Hypertension means you need to limit sodium."},
    {"id": "N05", "cat": "need", "if": "condition(high_cholesterol)", "then": "need(high_fiber)", "type": "derive",
     "text": "High cholesterol improves with soluble fibre."},
    {"id": "N06", "cat": "need", "if": "condition(anemia)", "then": "need(iron)", "type": "derive",
     "text": "Anaemia means you need iron-rich foods."},
    {"id": "N07", "cat": "need", "if": "stage(pregnancy)", "then": "need(folate)", "type": "derive",
     "text": "Pregnancy increases folate requirements."},
    {"id": "N08", "cat": "need", "if": "stage(pregnancy)", "then": "need(high_protein)", "type": "derive",
     "text": "Pregnancy increases protein requirements."},
    {"id": "N09", "cat": "need", "if": "goal(muscle_gain)", "then": "need(high_protein)", "type": "derive",
     "text": "Building muscle needs high protein."},
    {"id": "N10", "cat": "need", "if": "goal(weight_loss)", "then": "need(high_fiber)", "type": "derive",
     "text": "Fibre keeps you full while losing weight."},
    {"id": "N11", "cat": "need", "if": "goal(weight_loss)", "then": "need(light_meals)", "type": "derive",
     "text": "Weight loss favours lighter, lower-calorie meals."},
    {"id": "N12", "cat": "need", "if": "bmi(underweight)", "then": "need(energy_dense)", "type": "derive",
     "text": "Underweight BMI needs energy-dense meals."},
    {"id": "N13", "cat": "need", "if": "goal(weight_gain)", "then": "need(energy_dense)", "type": "derive",
     "text": "Gaining weight needs energy-dense meals."},
    {"id": "N14", "cat": "need", "if": "bmi(overweight)", "then": "need(light_meals)", "type": "derive",
     "text": "Overweight BMI favours lighter meals."},
    {"id": "N15", "cat": "need", "if": "bmi(obese)", "then": "need(light_meals)", "type": "derive",
     "text": "BMI in the obesity range favours lighter meals."},
    {"id": "N16", "cat": "need", "if": "stage(senior)", "then": "need(high_protein)", "type": "derive",
     "text": "Seniors need more protein to protect muscle."},

    # ---- allergy and diet safety (hard rules) ----------------------------
    {"id": "A01", "cat": "allergy", "if": "allergy(?a) AND contains(?a)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains {a}, which you are allergic to."},
    {"id": "D01", "cat": "diet", "if": "diet(vegan) AND item(animal_product)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains animal products, but you follow a vegan diet."},
    {"id": "D02", "cat": "diet", "if": "diet(vegetarian) AND item(meat)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains meat, but you are vegetarian."},
    {"id": "D03", "cat": "diet", "if": "diet(vegetarian) AND item(fish)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains fish, but you are vegetarian."},
    {"id": "D04", "cat": "diet", "if": "diet(eggetarian) AND item(meat)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains meat, but you are eggetarian."},
    {"id": "D05", "cat": "diet", "if": "diet(eggetarian) AND item(fish)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains fish, but you are eggetarian."},
    {"id": "D06", "cat": "diet", "if": "diet(pescatarian) AND item(meat)", "then": "reject", "type": "reject",
     "weight": 100, "text": "Contains meat, but you are pescatarian."},

    # ---- medical rules ---------------------------------------------------
    {"id": "M01", "cat": "medical", "if": "condition(diabetes) AND need(low_gi) AND item(high_gi)",
     "then": "reject", "type": "reject", "weight": 100,
     "text": "High glycaemic index is unsuitable with diabetes."},
    {"id": "M02", "cat": "medical", "if": "need(low_gi) AND item(high_gi) AND NOT condition(diabetes)",
     "then": "caution", "type": "caution", "weight": 30,
     "text": "High glycaemic index; you are better off with low-GI choices."},
    {"id": "M03", "cat": "medical", "if": "need(low_gi) AND item(low_gi)", "then": "prefer", "type": "prefer",
     "weight": 20, "text": "Low glycaemic index supports your blood-sugar goal."},
    {"id": "M04", "cat": "medical", "if": "need(low_sodium) AND item(high_sodium)", "then": "caution",
     "type": "caution", "weight": 50, "text": "High sodium is a concern with hypertension."},
    {"id": "M05", "cat": "medical", "if": "need(low_sodium) AND item(low_sodium)", "then": "prefer", "type": "prefer",
     "weight": 10, "text": "Low sodium suits your blood-pressure goal."},
    {"id": "M06", "cat": "medical", "if": "condition(high_cholesterol) AND item(fried)", "then": "caution",
     "type": "caution", "weight": 40, "text": "Deep-fried food raises cholesterol risk."},
    {"id": "M07", "cat": "medical", "if": "need(high_fiber) AND item(high_fiber)", "then": "prefer", "type": "prefer",
     "weight": 15, "text": "High fibre supports your health goal."},
    {"id": "M08", "cat": "medical", "if": "need(iron) AND item(iron_rich)", "then": "prefer", "type": "prefer",
     "weight": 20, "text": "Iron-rich food helps with anaemia."},
    {"id": "M09", "cat": "life_stage", "if": "need(folate) AND item(folate_rich)", "then": "prefer", "type": "prefer",
     "weight": 20, "text": "Folate-rich food supports a healthy pregnancy."},
    {"id": "M10", "cat": "life_stage", "if": "stage(pregnancy) AND item(unsafe_pregnancy)", "then": "reject",
     "type": "reject", "weight": 100, "text": "Raw fish, alcohol or unpasteurised foods are unsafe in pregnancy."},

    # ---- goal and BMI rules ---------------------------------------------
    {"id": "G01", "cat": "goal", "if": "need(high_protein) AND item(high_protein)", "then": "prefer", "type": "prefer",
     "weight": 20, "text": "High protein supports your goal."},
    {"id": "G02", "cat": "bmi", "if": "need(light_meals) AND item(calorie_dense)", "then": "caution",
     "type": "caution", "weight": 25, "text": "Calorie-dense meal; lighter options fit your BMI/goal better."},
    {"id": "G03", "cat": "bmi", "if": "need(light_meals) AND item(light)", "then": "prefer", "type": "prefer",
     "weight": 8, "text": "A lighter meal fits your BMI/goal."},
    {"id": "G04", "cat": "bmi", "if": "need(energy_dense) AND item(calorie_dense)", "then": "prefer", "type": "prefer",
     "weight": 20, "text": "Energy-dense meal helps you reach a healthy weight."},
    {"id": "G05", "cat": "bmi", "if": "need(energy_dense) AND item(light)", "then": "caution", "type": "caution",
     "weight": 10, "text": "Too light to help you gain weight."},
    {"id": "G06", "cat": "goal", "if": "goal(weight_loss) AND item(high_sugar)", "then": "caution", "type": "caution",
     "weight": 20, "text": "Sugary food slows weight loss."},
    {"id": "G07", "cat": "goal", "if": "goal(weight_loss) AND item(fried)", "then": "caution", "type": "caution",
     "weight": 15, "text": "Fried food adds extra calories."},
    {"id": "G08", "cat": "bmi", "if": "bmi(obese) AND item(high_sugar)", "then": "caution", "type": "caution",
     "weight": 20, "text": "Sugary food is best limited at your BMI."},
]

CATEGORIES = {
    "need": "Need derivation",
    "allergy": "Allergy safety",
    "diet": "Dietary preference",
    "medical": "Medical condition",
    "life_stage": "Life stage",
    "goal": "Fitness goal",
    "bmi": "BMI category",
}

# ---------------------------------------------------------------------------
# Parsing helpers (strings -> tuples) used by the inference engine
# ---------------------------------------------------------------------------
_ATOM = re.compile(r"^\s*(NOT\s+)?(\w+)\(([^)]*)\)\s*$", re.IGNORECASE)


def parse_atom(text: str) -> tuple[bool, str, tuple[str, ...]]:
    """'NOT condition(diabetes)' -> (True, 'condition', ('diabetes',))"""
    m = _ATOM.match(text)
    if not m:
        raise ValueError(f"Bad atom: {text!r}")
    neg, pred, args = m.groups()
    return bool(neg), pred.lower(), tuple(a.strip().lower() for a in args.split(",") if a.strip())


def compile_rules(rules: list[dict] | None = None) -> list[dict]:
    compiled = []
    for r in rules or RULES:
        conds = [parse_atom(part) for part in re.split(r"\s+AND\s+", r["if"], flags=re.IGNORECASE)]
        if r["type"] == "derive":
            _, pred, args = parse_atom(r["then"])
            head = (pred, args)
        else:
            head = (r["type"], ())
        compiled.append({**r, "conds": conds, "head": head, "weight": r.get("weight", 0)})
    return compiled
