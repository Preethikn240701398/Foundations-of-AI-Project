"""
Units I-II - search strategies used to assemble a day of meals and to improve a week.

* bfs_day     : Breadth-First Search (uninformed) - explores every combination level by level
* astar_day   : A* (informed) - f(n) = g(n) + h(n) with an admissible heuristic
* anneal_week : Simulated annealing (local search) - swaps single meals to lower a cost function
* rank_uncertain : belief-state ranking for the food scanner (partially observable environment)
"""
from __future__ import annotations

import heapq
import math
import random
from collections import Counter, deque


def _valid(meal: dict, slot: str, chosen: list[dict], usage: Counter, banned: dict, max_repeat: int) -> bool:
    if any(c["name"] == meal["name"] for c in chosen):
        return False
    if usage[meal["name"]] >= max_repeat:
        return False
    if meal["name"] in banned.get(slot, ()):
        return False
    return True


def bfs_day(slots, domains, *, target_kcal, tol=0.12, usage=None, banned=None, max_repeat=2, max_nodes=30000):
    """Uninformed search: first complete plan whose calories fall inside the window."""
    usage, banned = usage or Counter(), banned or {}
    queue = deque([([], 0)])
    stats = {"nodes": 0, "frontier_max": 1}
    while queue and stats["nodes"] < max_nodes:
        chosen, total = queue.popleft()
        stats["nodes"] += 1
        if len(chosen) == len(slots):
            if abs(total - target_kcal) <= target_kcal * tol:
                return dict(zip(slots, chosen)), stats
            continue
        slot = slots[len(chosen)]
        for meal in domains.get(slot, []):
            if _valid(meal, slot, chosen, usage, banned, max_repeat):
                queue.append((chosen + [meal], total + meal["calories"]))
        stats["frontier_max"] = max(stats["frontier_max"], len(queue))
    return None, stats


def astar_day(slots, domains, *, usage=None, banned=None, max_repeat=2, max_nodes=30000):
    """
    Informed search. Every meal carries a non-negative `cost` (calorie misfit + low rank).
    g(n) = sum of costs chosen so far, h(n) = sum of the cheapest remaining option per slot.
    h never over-estimates, so the first complete plan popped is optimal for this cost model.
    """
    usage, banned = usage or Counter(), banned or {}
    min_cost = {s: min((m["cost"] for m in domains.get(s, [])), default=0.0) for s in slots}
    counter = 0
    frontier = [(sum(min_cost.values()), 0, 0.0, [])]
    stats = {"nodes": 0, "frontier_max": 1}
    while frontier and stats["nodes"] < max_nodes:
        _f, _c, g, chosen = heapq.heappop(frontier)
        stats["nodes"] += 1
        if len(chosen) == len(slots):
            return dict(zip(slots, chosen)), stats
        slot = slots[len(chosen)]
        rest = sum(min_cost[s] for s in slots[len(chosen) + 1:])
        for meal in domains.get(slot, []):
            if _valid(meal, slot, chosen, usage, banned, max_repeat):
                counter += 1
                g2 = g + meal["cost"]
                heapq.heappush(frontier, (g2 + rest, counter, g2, chosen + [meal]))
        stats["frontier_max"] = max(stats["frontier_max"], len(frontier))
    return None, stats


def anneal_week(week: list[dict], pools: list[dict], cost_fn, *, iterations=1500, t_start=6.0, t_end=0.05,
                max_repeat=3, seed=7):
    """
    Simulated annealing over a whole week.
    week  : list (one per day) of {slot: meal}
    pools : list (one per day) of {slot: [candidate meals]}
    cost_fn(week) -> float (lower is better)
    A worse neighbour is accepted with probability exp(-delta / T) so the search can escape local minima.
    """
    rng = random.Random(seed)
    current = [dict(d) for d in week]
    cur_cost = cost_fn(current)
    best, best_cost = [dict(d) for d in current], cur_cost
    start_cost = cur_cost
    accepted = 0
    for i in range(iterations):
        t = t_start * (t_end / t_start) ** (i / max(iterations - 1, 1))
        d = rng.randrange(len(current))
        slot = rng.choice(list(current[d].keys()))
        options = pools[d].get(slot) or []
        if len(options) < 2:
            continue
        cand = rng.choice(options)
        if cand["name"] == current[d][slot]["name"]:
            continue
        if any(m["name"] == cand["name"] for s, m in current[d].items() if s != slot):
            continue
        usage = Counter(m["name"] for day in current for m in day.values())
        if usage[cand["name"]] >= max_repeat:
            continue
        neighbour = [dict(x) for x in current]
        neighbour[d][slot] = cand
        new_cost = cost_fn(neighbour)
        delta = new_cost - cur_cost
        if delta < 0 or rng.random() < math.exp(-delta / max(t, 1e-9)):
            current, cur_cost = neighbour, new_cost
            accepted += 1
            if cur_cost < best_cost:
                best, best_cost = [dict(x) for x in current], cur_cost
    return best, {"iterations": iterations, "accepted": accepted, "cost_before": round(start_cost, 2),
                  "cost_after": round(best_cost, 2)}


def rank_uncertain(candidates: list[dict], query: str, threshold: float = 0.65):
    """
    Search in a partially observable environment: the scanner cannot be sure what the food is,
    so it keeps a ranked belief state and asks for confirmation when the best guess is weak.
    """
    q = (query or "").lower().strip()
    tokens = {t for t in q.replace("-", " ").replace(",", " ").split() if len(t) > 1}
    ranked = []
    for item in candidates:
        name = str(item.get("name") or "").lower()
        tags = [str(t).lower() for t in item.get("tags") or []]
        hay = " ".join([name, *tags])
        score = 0.0
        if q and name == q:
            score = 0.99
        elif q and q in name:
            score = 0.9
        elif q and q in hay:
            score = 0.7
        elif tokens:
            name_tokens = set(name.replace("&", " ").split())
            hits = len(tokens & name_tokens)
            tag_hits = sum(1 for t in tokens if t in " ".join(tags))
            score = min(0.85, (hits * 0.6 + tag_hits * 0.2) / max(len(tokens), 1) + (0.1 if hits else 0))
        ranked.append({**item, "confidence": round(min(score, 0.99), 3)})
    ranked.sort(key=lambda x: x["confidence"], reverse=True)
    top = [r for r in ranked[:6] if r["confidence"] > 0] or ranked[:3]
    best = top[0]["confidence"] if top else 0.0
    return {"candidates": top, "needs_confirmation": best < threshold}
