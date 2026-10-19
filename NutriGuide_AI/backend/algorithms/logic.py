"""
Step 5 of the implementation pipeline - the Inference Engine (syllabus Unit IV).

* Forward chaining  : start from known facts (user + food) and fire rules until nothing new
                      can be derived. Every firing is recorded in a trace.
* Backward chaining : start from a goal ("is this meal preferred?") and work back through
                      the rules to the facts that prove it, returning a proof tree.
* Unification       : rule variables such as ?a are bound to constants (first-order logic).
* Negation as failure: "NOT condition(diabetes)" holds when the fact is absent.

No FastAPI / MongoDB imports - the engine is a pure, testable module.
"""
from __future__ import annotations

from algorithms import knowledge_base as kb
from algorithms.nutrition import compute_requirements, conditions_of

Fact = tuple  # (predicate, arg1, arg2, ...)

_COMPILED = kb.compile_rules()


# ---------------------------------------------------------------------------
# Fact construction
# ---------------------------------------------------------------------------
def user_facts(profile: dict) -> set[Fact]:
    """Turn a stored profile into symbolic facts."""
    facts: set[Fact] = set()
    req = compute_requirements(profile)
    for c in conditions_of(profile):
        facts.add(("condition", c))
    for a in profile.get("allergies") or []:
        facts.add(("allergy", kb.normalize_allergen(a)))
    for d in profile.get("dietary_restrictions") or []:
        facts.add(("diet", str(d).strip().lower()))
    stage = str(profile.get("life_stage") or "adult").lower()
    facts.add(("stage", stage))
    if stage == "adult" and int(profile.get("age") or 0) >= 60:
        facts.add(("stage", "senior"))
    facts.add(("goal", req["goal"]))
    facts.add(("bmi", req["bmi_category"]))
    return facts


def item_facts(item: dict, profile: dict | None = None) -> set[Fact]:
    facts: set[Fact] = set()
    for p in kb.item_properties(item, profile):
        facts.add(("item", p))
    for a in kb.item_contains(item):
        facts.add(("contains", a))
    return facts


# ---------------------------------------------------------------------------
# Unification helpers
# ---------------------------------------------------------------------------
def _is_var(token: str) -> bool:
    return isinstance(token, str) and token.startswith("?")


def _unify(pattern: tuple, fact: tuple, binding: dict) -> dict | None:
    """Match one pattern against one fact under an existing binding."""
    if len(pattern) != len(fact) or pattern[0] != fact[0]:
        return None
    new = dict(binding)
    for p, f in zip(pattern[1:], fact[1:]):
        if _is_var(p):
            if p in new and new[p] != f:
                return None
            new[p] = f
        elif p != f:
            return None
    return new


def _substitute(args: tuple, binding: dict) -> tuple:
    return tuple(binding.get(a, a) if _is_var(a) else a for a in args)


def _match_conditions(conds, facts: set[Fact], binding: dict, used: tuple = ()):
    """Yield (binding, supporting_facts) for every way the conditions can be satisfied."""
    if not conds:
        yield binding, used
        return
    (neg, pred, args), rest = conds[0], conds[1:]
    pattern = (pred, *_substitute(args, binding))
    if neg:
        if not any(_unify(pattern, f, binding) is not None for f in facts):
            yield from _match_conditions(rest, facts, binding, used)
        return
    for f in sorted(facts):
        b = _unify(pattern, f, binding)
        if b is not None:
            yield from _match_conditions(rest, facts, b, used + (f,))


def _fmt(fact: tuple) -> str:
    return f"{fact[0]}({', '.join(fact[1:])})" if len(fact) > 1 else f"{fact[0]}"


def _bind_text(rule: dict, binding: dict) -> str:
    return rule["text"].format(**{k.lstrip("?"): v for k, v in binding.items()})


# ---------------------------------------------------------------------------
# Forward chaining
# ---------------------------------------------------------------------------
def forward_chain(facts: set[Fact], rules: list[dict] | None = None, max_cycles: int = 12) -> dict:
    """
    Run the recognise-act cycle until no rule can add anything new.
    Returns {facts, derived, fired, memory}; `fired` is the ordered trace of rule firings.
    """
    rules = rules or _COMPILED
    wm: set[Fact] = set(facts)
    fired: list[dict] = []
    seen: set[tuple] = set()
    # conflict resolution: derive-rules first (they enable others), then safety (heavier) first
    order = sorted(rules, key=lambda r: (r["type"] != "derive", -r["weight"], r["id"]))

    for cycle in range(1, max_cycles + 1):
        changed = False
        for rule in order:
            for binding, support in list(_match_conditions(rule["conds"], wm, {})):
                key = (rule["id"], tuple(sorted(binding.items())))
                if key in seen:
                    continue
                seen.add(key)
                entry = {
                    "cycle": cycle,
                    "rule_id": rule["id"],
                    "category": rule["cat"],
                    "type": rule["type"],
                    "weight": rule["weight"],
                    "text": _bind_text(rule, binding),
                    "if": rule["if"],
                    "then": rule["then"],
                    "bindings": {k.lstrip("?"): v for k, v in binding.items()},
                    "because": [_fmt(f) for f in support],
                }
                if rule["type"] == "derive":
                    pred, args = rule["head"]
                    new_fact = (pred, *_substitute(args, binding))
                    entry["adds"] = _fmt(new_fact)
                    if new_fact not in wm:
                        wm.add(new_fact)
                        changed = True
                        fired.append(entry)
                else:
                    fired.append(entry)
                    changed = True
        if not changed:
            break
    derived = sorted(_fmt(f) for f in wm - set(facts))
    return {"facts": sorted(_fmt(f) for f in facts), "derived": derived, "fired": fired, "memory": wm}


# ---------------------------------------------------------------------------
# Backward chaining
# ---------------------------------------------------------------------------
def _prove(pattern: tuple, facts: set[Fact], rules: list[dict], binding: dict, depth: int, max_depth: int):
    pat = (pattern[0], *_substitute(pattern[1:], binding))
    for f in sorted(facts):
        b = _unify(pat, f, binding)
        if b is not None:
            yield b, {"goal": _fmt(f), "by": "known fact", "children": []}
    if depth >= max_depth:
        return
    for rule in rules:
        if rule["type"] == "derive":
            head_pred, head_args = rule["head"]
            hb = _unify((head_pred, *head_args), pat, binding)
        else:
            hb = binding if (len(pat) == 1 and pat[0] == rule["type"]) else None
        if hb is None:
            continue
        for b2, children in _solve(rule["conds"], facts, rules, hb, depth + 1, max_depth):
            yield b2, {"goal": _fmt(pat), "by": f"{rule['id']}: {_bind_text(rule, b2)}", "children": children}


def _solve(conds, facts, rules, binding, depth, max_depth):
    if not conds:
        yield binding, []
        return
    (neg, pred, args), rest = conds[0], conds[1:]
    if neg:
        pat = (pred, *_substitute(args, binding))
        if any(_unify(pat, f, binding) is not None for f in facts):
            return
        leaf = {"goal": f"NOT {_fmt(pat)}", "by": "negation as failure", "children": []}
        for b2, tail in _solve(rest, facts, rules, binding, depth, max_depth):
            yield b2, [leaf] + tail
        return
    for b1, proof in _prove((pred, *args), facts, rules, binding, depth, max_depth):
        for b2, tail in _solve(rest, facts, rules, b1, depth, max_depth):
            yield b2, [proof] + tail


def backward_chain(goal: str, facts: set[Fact], rules: list[dict] | None = None, max_depth: int = 6) -> dict | None:
    """
    Prove a goal such as 'need(low_gi)' or 'prefer' by working backwards through the rules.
    Returns a proof tree {goal, by, children}, or None if it cannot be proven.
    """
    rules = rules or _COMPILED
    text = goal if "(" in goal else f"{goal}()"
    _, pred, args = kb.parse_atom(text)
    pattern = (pred, *args)
    for _b, proof in _prove(pattern, facts, rules, {}, 0, max_depth):
        return proof
    return None


# ---------------------------------------------------------------------------
# High level API used by routers
# ---------------------------------------------------------------------------
def evaluate_item(profile: dict, item: dict, base_facts: set[Fact] | None = None) -> dict:
    """Run the engine for one meal/food and summarise the verdict."""
    ufacts = base_facts if base_facts is not None else user_facts(profile)
    facts = set(ufacts) | item_facts(item, profile)
    result = forward_chain(facts)
    score = 0
    reasons = {"reject": [], "caution": [], "prefer": []}
    for f in result["fired"]:
        if f["type"] == "derive":
            continue
        reasons[f["type"]].append(f)
        score += {"reject": -f["weight"] * 10, "caution": -f["weight"], "prefer": f["weight"]}[f["type"]]
    if reasons["reject"]:
        verdict = "avoid"
    elif reasons["caution"] and score < 0:
        verdict = "caution"
    elif reasons["prefer"]:
        verdict = "recommended"
    else:
        verdict = "neutral"
    return {
        "verdict": verdict,
        "score": score,
        "reasons": reasons,
        "fired": result["fired"],
        "derived": result["derived"],
        "facts": result["facts"],
        "memory": result["memory"],
        "base": facts,
    }


def public_view(evaluation: dict) -> dict:
    """Strip non-serialisable fields."""
    return {k: v for k, v in evaluation.items() if k not in {"memory", "base"}}


def prove_verdict(evaluation: dict) -> dict | None:
    """Backward-chain from the verdict back to the facts that support it."""
    goal = {"avoid": "reject", "caution": "caution", "recommended": "prefer"}.get(evaluation["verdict"])
    if not goal:
        return None
    return backward_chain(goal, evaluation["base"])


def rule_catalogue() -> list[dict]:
    return [{k: v for k, v in r.items() if k not in {"conds", "head"}} for r in _COMPILED]
