"""
Steps 6 and 7 of the implementation pipeline - meal selection, recommendation and diet-plan generation.

Pipeline for every request
  1. Inference engine evaluates every meal against the user's facts  -> safe / caution / avoid
  2. Meals that are 'avoid' are removed (hard safety).  The rest are ranked:
         rank = rule score + learned preference (reinforcement weights) + calorie fit to the slot
  3. Each meal gets a portion size (0.75x - 2x) so it lands near the slot's calorie share
  4. A search algorithm (CSP / A* / BFS) picks one meal per slot, repeated for each day
  5. Optional simulated-annealing pass improves the whole week
  6. Portions are calibrated so the day lands on the calorie target
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from algorithms import csp, logic, ml, search
from algorithms.nutrition import compute_requirements, conditions_of

SLOT_SHARES_4 = {"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.30, "Snack": 0.10}
SLOT_SHARES_3 = {"Breakfast": 0.28, "Lunch": 0.38, "Dinner": 0.34}
PORTIONS = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
MAX_PORTION = 2.0
SCALED_FIELDS = ["calories", "protein", "carbs", "fat", "fiber", "sodium_mg"]


class PlanError(Exception):
    pass


# ---------------------------------------------------------------------------
def slot_targets(slots: list[str], kcal: float) -> dict[str, float]:
    shares = SLOT_SHARES_4 if "Snack" in slots else SLOT_SHARES_3
    total = sum(shares.get(s, 0.2) for s in slots)
    return {s: kcal * shares.get(s, 0.2) / total for s in slots}


def scale_meal(meal: dict, portion: float) -> dict:
    out = dict(meal)
    base = meal.get("base") or {f: meal.get(f, 0) or 0 for f in SCALED_FIELDS}
    out["base"] = base
    out["portion"] = portion
    for f in SCALED_FIELDS:
        v = float(base.get(f, 0) or 0) * portion
        out[f] = int(round(v)) if f in {"calories", "sodium_mg"} else round(v, 1)
    return out


def nearest_portion(meal_kcal: float, target: float) -> float:
    if meal_kcal <= 0:
        return 1.0
    ratio = target / meal_kcal
    return min(PORTIONS, key=lambda p: abs(p - ratio))


# ---------------------------------------------------------------------------
def rank_catalogue(profile: dict, meals: list[dict], weights: dict | None = None) -> list[dict]:
    """Evaluate every meal with the inference engine (used by the Meals page)."""
    weights = weights or profile.get("rl_weights") or {}
    base_facts = logic.user_facts(profile)
    out = []
    for m in meals:
        ev = logic.evaluate_item(profile, m, base_facts)
        pref = ml.score_meal(m, weights) * 10
        out.append({**m, "verdict": ev["verdict"], "engine_score": ev["score"], "preference": round(pref, 2),
                    "match": ev["score"] + pref,
                    "why": _why(ev)})
    return out


def _why(ev: dict, limit: int = 3) -> list[dict]:
    items = ev["reasons"]["reject"] + ev["reasons"]["caution"] + ev["reasons"]["prefer"]
    return [{"rule": r["rule_id"], "type": r["type"], "text": r["text"]} for r in items[:limit]]


def build_pools(profile: dict, meals: list[dict], slots: list[str], targets: dict[str, float],
                weights: dict | None = None, top_k: int = 9) -> dict[str, list[dict]]:
    """Safe, ranked, portion-scaled candidate meals for every slot."""
    weights = weights or profile.get("rl_weights") or {}
    base_facts = logic.user_facts(profile)
    evals = {m["name"]: logic.evaluate_item(profile, m, base_facts) for m in meals}
    pools: dict[str, list[dict]] = {}
    for slot in slots:
        pool = []
        for m in meals:
            if slot not in (m.get("meal_type") or []):
                continue
            ev = evals[m["name"]]
            if ev["verdict"] == "avoid":
                continue
            portion = nearest_portion(float(m.get("calories") or 0), targets[slot])
            scaled = scale_meal(m, portion)
            fit = abs(scaled["calories"] - targets[slot]) / max(targets[slot], 1)
            pref = ml.score_meal(m, weights) * 10
            rank = ev["score"] + pref - fit * 60
            cost = fit * 100 + max(0.0, 60 - (ev["score"] + pref)) * 0.35
            pool.append({**scaled, "verdict": ev["verdict"], "engine_score": ev["score"], "rank": rank,
                         "cost": max(cost, 0.0), "why": _why(ev)})
        pool.sort(key=lambda x: -x["rank"])
        if not pool:
            raise PlanError(f"No safe {slot.lower()} options match your allergies, diet and health rules.")
        pools[slot] = pool[:top_k]
    return pools


# ---------------------------------------------------------------------------
def calibrate_day(day: dict[str, dict], target_kcal: float) -> dict[str, dict]:
    """Nudge portion sizes (in 0.25 steps) so the day total approaches the calorie target."""
    day = dict(day)
    for _ in range(4):
        total = sum(m["calories"] for m in day.values())
        if total <= 0 or abs(total - target_kcal) / target_kcal < 0.02:
            break
        factor = target_kcal / total
        changed = False
        for slot, m in list(day.items()):
            new_p = round(min(max(m["portion"] * factor, 0.75), MAX_PORTION) * 4) / 4
            if abs(new_p - m["portion"]) >= 0.25:
                day[slot] = scale_meal(m, new_p)
                changed = True
        if not changed:
            break
    return day


def day_totals(day: dict[str, dict]) -> dict:
    meals = list(day.values())
    n = len(meals) or 1
    tot = {f: round(sum(float(m.get(f) or 0) for m in meals), 1) for f in SCALED_FIELDS}
    tot["calories"] = int(tot["calories"])
    tot["sodium_mg"] = int(tot["sodium_mg"])
    tot["gi_avg"] = round(sum(float(m.get("glycemic_index") or 0) for m in meals) / n)
    return tot


def _week_cost(week, targets_day, protein_min, slots):
    def cost(w):
        c = 0.0
        usage = Counter()
        for day in w:
            tot = sum(m["calories"] for m in day.values())
            prot = sum(m["protein"] for m in day.values())
            c += abs(tot - targets_day) / targets_day * 200
            c += max(0.0, protein_min - prot) / max(protein_min, 1) * 120
            c -= sum(m.get("rank", 0) for m in day.values()) * 0.04
            for m in day.values():
                usage[m["name"]] += 1
        c += sum(max(0, n - 2) * 12 for n in usage.values())
        return c
    return cost


# ---------------------------------------------------------------------------
def generate_plan(profile: dict, meals: list[dict], *, days: int = 7, strategy: str = "csp",
                  optimize: bool = True, meals_per_day: int | None = None, start: date | None = None) -> dict:
    """Generate a multi-day diet plan. Raises PlanError when no safe plan exists."""
    req = compute_requirements(profile)
    mpd = meals_per_day or int(profile.get("meals_per_day") or 4)
    slots = ["Breakfast", "Lunch", "Dinner", "Snack"] if mpd >= 4 else ["Breakfast", "Lunch", "Dinner"]
    target = float(profile.get("daily_calories_target") or req["calories"])
    protein_target = float(profile.get("protein_target") or req["protein_g"])
    targets = slot_targets(slots, target)
    weights = profile.get("rl_weights") or {}
    pools = build_pools(profile, meals, slots, targets, weights)
    sodium_max = req["sodium_limit_mg"] if "hypertension" in conditions_of(profile) else None

    usage: Counter = Counter()
    banned: dict[str, set] = {s: set() for s in slots}
    week: list[dict] = []
    agg = {"nodes": 0, "backtracks": 0, "pruned": 0}
    relax_levels: list[str] = []
    strategy = (strategy or "csp").lower()

    for _ in range(days):
        if strategy == "bfs":
            sol, st = search.bfs_day(slots, pools, target_kcal=target, usage=usage, banned=banned)
            relax = "n/a"
        elif strategy == "astar":
            sol, st = search.astar_day(slots, pools, usage=usage, banned=banned)
            relax = "n/a"
        else:
            sol, st = csp.solve_with_relaxation(slots, pools, target_kcal=target, protein_min=protein_target,
                                                usage=usage, banned=banned, sodium_max=sodium_max)
            relax = st.get("relaxation", "failed")
        for k in agg:
            agg[k] += st.get(k, 0)
        if not sol and strategy in {"bfs", "astar"}:  # search found nothing: fall back to the CSP relaxation ladder
            sol, st2 = csp.solve_with_relaxation(slots, pools, target_kcal=target, protein_min=protein_target,
                                                 usage=usage, banned=banned, sodium_max=sodium_max)
            relax = "csp-fallback" if sol else "fallback"
        if not sol:  # last resort so the user always gets a plan: best-ranked safe meal per slot
            sol = {s: next((m for m in pools[s] if usage[m["name"]] < 3 and m["name"] not in banned[s]),
                           pools[s][0]) for s in slots}
            relax = "fallback"
        relax_levels.append(relax)
        week.append(sol)
        for s, m in sol.items():
            usage[m["name"]] += 1
            banned[s] = {m["name"]}

    anneal_stats = None
    if optimize and days > 1:
        cost_fn = _week_cost(week, target, protein_target, slots)
        week, anneal_stats = search.anneal_week(week, [pools] * days, cost_fn)

    week = [calibrate_day(d, target) for d in week]

    start = start or date.today()
    out_days = []
    for i, d in enumerate(week):
        tot = day_totals(d)
        dt = start + timedelta(days=i)
        out_days.append({
            "index": i,
            "date": dt.isoformat(),
            "weekday": dt.strftime("%a"),
            "meals": [{"slot": s, **_public_meal(d[s])} for s in slots],
            "totals": tot,
            "accuracy": round(100 - abs(tot["calories"] - target) / target * 100, 1),
        })
    avg = lambda key: round(sum(x["totals"][key] for x in out_days) / len(out_days), 1)
    return {
        "strategy": strategy,
        "slots": slots,
        "days": out_days,
        "targets": {"calories": int(target), "protein": int(protein_target), "carbs": req["carbs_g"],
                    "fat": req["fat_g"], "fiber": req["fiber_g"], "sodium_limit": req["sodium_limit_mg"],
                    "glycemic_max": req["glycemic_max"]},
        "summary": {
            "avg_calories": avg("calories"), "avg_protein": avg("protein"), "avg_carbs": avg("carbs"),
            "avg_fat": avg("fat"), "avg_fiber": avg("fiber"),
            "avg_accuracy": round(sum(x["accuracy"] for x in out_days) / len(out_days), 1),
            "unique_meals": len({m["name"] for d in out_days for m in d["meals"]}),
        },
        "algorithm": {"strategy": strategy, **agg, "relaxation": relax_levels,
                      "annealing": anneal_stats, "candidates_per_slot": {s: len(pools[s]) for s in slots}},
    }


def _public_meal(m: dict) -> dict:
    keep = ["id", "name", "emoji", "cuisine", "meal_type", "ingredients", "steps", "tags", "allergens",
            "calories", "protein", "carbs", "fat", "fiber", "sodium_mg", "glycemic_index", "prep_minutes",
            "portion", "verdict", "why", "base"]
    return {k: m.get(k) for k in keep if k in m}


def alternatives(profile: dict, meals: list[dict], slot: str, exclude: set[str], target_kcal: float,
                 limit: int = 6) -> list[dict]:
    """Safe replacement options for one slot, best first."""
    slots = ["Breakfast", "Lunch", "Dinner", "Snack"]
    targets = slot_targets(slots, target_kcal)
    pools = build_pools(profile, meals, [slot], {slot: targets.get(slot, target_kcal * 0.3)}, top_k=30)
    return [_public_meal(m) | {"rank": round(m["rank"], 1)} for m in pools[slot] if m["name"] not in exclude][:limit]
