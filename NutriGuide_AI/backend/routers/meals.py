from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from algorithms import logic, ml, planner
from auth_utils import get_current_user
from db import db, oid, serialize, utcnow
from models.schemas import FeedbackIn
from routers.common import load_meals
from routers.profiles import user_profile

router = APIRouter(prefix="/meals", tags=["meals"])

VERDICT_ORDER = {"recommended": 0, "neutral": 1, "caution": 2, "avoid": 3}


@router.get("")
async def catalogue(slot: str | None = None, q: str | None = None, verdict: str | None = None,
                    user=Depends(get_current_user)):
    """Meal selection: every meal is judged by the inference engine against *your* profile."""
    profile = serialize(await user_profile(user))
    meals = await load_meals()
    ranked = planner.rank_catalogue(profile, meals)
    if slot:
        ranked = [m for m in ranked if slot in (m.get("meal_type") or [])]
    if q:
        ql = q.lower()
        ranked = [m for m in ranked if ql in m["name"].lower() or ql in " ".join(m.get("tags") or []).lower()
                  or ql in " ".join(m.get("ingredients") or []).lower()]
    if verdict:
        ranked = [m for m in ranked if m["verdict"] == verdict]
    ranked.sort(key=lambda m: (VERDICT_ORDER[m["verdict"]], -m["match"]))
    counts = {v: 0 for v in VERDICT_ORDER}
    for m in ranked:
        counts[m["verdict"]] += 1
    return {"meals": ranked, "counts": counts}


@router.get("/{meal_id}")
async def detail(meal_id: str, user=Depends(get_current_user)):
    profile = serialize(await user_profile(user))
    meal = await db.col("meals").find_one({"_id": ObjectId(meal_id)})
    if not meal:
        raise HTTPException(404, "Meal not found")
    meal = serialize(meal)
    ev = logic.evaluate_item(profile, meal)
    return {"meal": meal, "evaluation": logic.public_view(ev), "proof": logic.prove_verdict(ev)}


@router.post("/feedback")
async def feedback(body: FeedbackIn, user=Depends(get_current_user)):
    """Reinforcement-style learning: accepted meals raise the weight of their tags, rejected lower it."""
    profile = await user_profile(user)
    reward = 1.0 if body.accepted else -1.0
    tags = body.tags
    if not tags:
        meal = next((m for m in await load_meals() if m["name"] == body.meal_name), None)
        tags = (meal or {}).get("tags") or []
    weights = ml.update_rl_weights(profile.get("rl_weights") or {}, tags, reward)
    await db.col("profiles").update_one({"_id": profile["_id"]}, {"$set": {"rl_weights": weights}})
    await db.col("logs").insert_one({"_id": oid(), "user_id": ObjectId(user["id"]), "type": "feedback",
                                      "meal": body.meal_name, "accepted": body.accepted, "tags": tags,
                                      "date": utcnow().date().isoformat(), "created_at": utcnow()})
    return {"ok": True, "reward": reward, "rl_weights": weights}
