"""
Unit III - Constraint Satisfaction Problem (CSP) for one day of meals.

Variables   : meal slots            (Breakfast, Lunch, Dinner, Snack)
Domains     : safe meals for the slot (already filtered by the inference engine)
Constraints : 1. all-different      - no meal twice in a day
              2. calorie window     - day total within +/- tol of the target
              3. protein minimum    - day total >= protein_min
              4. variety            - a meal may appear at most `max_repeat` times per week
              5. not-same-as-yesterday for the same slot
              6. sodium ceiling     - optional (hypertension)

Techniques  : backtracking search, MRV variable ordering, value ordering by rank,
              forward checking (calorie / protein reachability bounds) and a relaxation ladder
              so the solver degrades gracefully instead of failing.
"""
from __future__ import annotations

from collections import Counter

RELAXATION_LADDER = [
    {"tol": 0.06, "protein": 0.90, "max_repeat": 2, "label": "strict"},
    {"tol": 0.10, "protein": 0.80, "max_repeat": 2, "label": "standard"},
    {"tol": 0.15, "protein": 0.70, "max_repeat": 3, "label": "relaxed"},
    {"tol": 0.25, "protein": 0.0, "max_repeat": 7, "label": "minimal"},
]


def solve_day(slots: list[str], domains: dict[str, list[dict]], *, target_kcal: float, protein_min: float,
              tol: float, max_repeat: int, usage: Counter | None = None, banned: dict[str, set] | None = None,
              sodium_max: float | None = None, max_nodes: int = 20000):
    usage = usage or Counter()
    banned = banned or {}
    stats = {"nodes": 0, "backtracks": 0, "pruned": 0}
    lo, hi = target_kcal * (1 - tol), target_kcal * (1 + tol)

    def allowed(slot: str, assignment: dict) -> list[dict]:
        used_today = {m["name"] for m in assignment.values()}
        out = []
        for m in domains.get(slot, []):
            if m["name"] in used_today:
                continue
            if usage[m["name"]] >= max_repeat:
                continue
            if m["name"] in banned.get(slot, ()):
                continue
            out.append(m)
        return out

    def search(assignment: dict, total_kcal: float, total_protein: float, total_sodium: float):
        if stats["nodes"] > max_nodes:
            return None
        stats["nodes"] += 1
        remaining = [s for s in slots if s not in assignment]
        if not remaining:
            ok = lo <= total_kcal <= hi and total_protein >= protein_min
            if sodium_max is not None and total_sodium > sodium_max:
                ok = False
            return dict(assignment) if ok else None

        # forward checking: shrink the domains of every unassigned slot
        filtered = {s: allowed(s, assignment) for s in remaining}
        if any(not v for v in filtered.values()):
            stats["pruned"] += 1
            return None
        min_k = sum(min(m["calories"] for m in v) for v in filtered.values())
        max_k = sum(max(m["calories"] for m in v) for v in filtered.values())
        max_p = sum(max(m["protein"] for m in v) for v in filtered.values())
        if total_kcal + min_k > hi or total_kcal + max_k < lo or total_protein + max_p < protein_min:
            stats["pruned"] += 1
            return None

        # MRV: most constrained slot first
        slot = min(remaining, key=lambda s: (len(filtered[s]), slots.index(s)))
        for meal in sorted(filtered[slot], key=lambda m: -m.get("rank", 0)):
            assignment[slot] = meal
            result = search(assignment, total_kcal + meal["calories"], total_protein + meal["protein"],
                            total_sodium + float(meal.get("sodium_mg") or 0))
            if result:
                return result
            del assignment[slot]
            stats["backtracks"] += 1
        return None

    solution = search({}, 0.0, 0.0, 0.0)
    return solution, stats


def solve_with_relaxation(slots, domains, *, target_kcal, protein_min, usage=None, banned=None,
                          sodium_max=None, start_level: int = 0):
    """Try progressively looser constraints; report which level succeeded."""
    totals = {"nodes": 0, "backtracks": 0, "pruned": 0}
    for i, level in enumerate(RELAXATION_LADDER[start_level:], start=start_level):
        solution, stats = solve_day(
            slots, domains, target_kcal=target_kcal, protein_min=protein_min * level["protein"],
            tol=level["tol"], max_repeat=level["max_repeat"], usage=usage, banned=banned,
            sodium_max=sodium_max if i < 3 else None,
        )
        for k in totals:
            totals[k] += stats[k]
        if solution:
            return solution, {**totals, "relaxation": level["label"], "level": i}
    return None, {**totals, "relaxation": "failed", "level": len(RELAXATION_LADDER)}
