from fastapi import APIRouter, Depends, HTTPException

from algorithms import knowledge_base as kb
from algorithms import logic
from algorithms.nutrition import compute_requirements
from auth_utils import get_current_user
from db import serialize
from models.schemas import InferIn
from routers.common import find_item, load_foods, load_meals
from routers.profiles import user_profile

router = APIRouter(prefix="/knowledge", tags=["knowledge-base"])


@router.get("/overview")
async def overview(user=Depends(get_current_user)):
    rules = logic.rule_catalogue()
    by_cat: dict[str, int] = {}
    for r in rules:
        by_cat[r["cat"]] = by_cat.get(r["cat"], 0) + 1
    return {
        "rule_count": len(rules),
        "categories": [{"id": k, "label": v, "count": by_cat.get(k, 0)} for k, v in kb.CATEGORIES.items()],
        "conditions": [{"id": k, **v} for k, v in kb.CONDITIONS.items()],
        "diets": [{"id": k, "summary": v} for k, v in kb.DIETS.items()],
        "allergens": kb.ALLERGENS,
        "thresholds": [{"property": k, "definition": v} for k, v in kb.THRESHOLDS.items()],
        "meal_count": len(await load_meals()),
        "food_count": len(await load_foods()),
    }


@router.get("/rules")
async def rules(user=Depends(get_current_user)):
    return {"rules": logic.rule_catalogue(), "categories": kb.CATEGORIES}


@router.get("/foods")
async def foods(user=Depends(get_current_user)):
    items = await load_foods()
    for f in items:
        f["properties"] = sorted(kb.item_properties(f))
        f["contains"] = sorted(kb.item_contains(f))
    return items


@router.post("/infer")
async def infer(body: InferIn, user=Depends(get_current_user)):
    """Run the inference engine on one food/meal. `overrides` lets you try 'what-if' profiles."""
    profile = serialize(await user_profile(user))
    for k, v in (body.overrides or {}).items():
        if v is not None:
            profile[k] = v
    item = find_item(body.item_name, await load_meals(), await load_foods())
    if not item:
        raise HTTPException(404, "I could not find that food or meal in the knowledge base")
    ev = logic.evaluate_item(profile, item)
    ufacts = sorted(f"{f[0]}({', '.join(f[1:])})" for f in logic.user_facts(profile))
    ifacts = sorted(f"{f[0]}({', '.join(f[1:])})" for f in logic.item_facts(item, profile))
    return {
        "item": item, "user_facts": ufacts, "item_facts": ifacts,
        "evaluation": logic.public_view(ev), "proof": logic.prove_verdict(ev),
        "requirements": compute_requirements(profile),
    }
