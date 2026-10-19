from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from algorithms import planner
from auth_utils import get_current_user
from db import db, oid, serialize, utcnow
from models.schemas import AlternativesIn, GeneratePlanIn, SavePlanIn
from routers.common import load_meals
from routers.profiles import user_profile

router = APIRouter(prefix="/diet-plans", tags=["diet-plans"])


def _summary(doc: dict) -> dict:
    d = serialize(doc)
    plan = d.get("plan") or {}
    return {"id": d["id"], "name": d.get("name"), "created_at": d.get("created_at"), "is_active": d.get("is_active", False),
            "days": len(plan.get("days", [])), "strategy": plan.get("strategy"),
            "avg_calories": (plan.get("summary") or {}).get("avg_calories"),
            "avg_accuracy": (plan.get("summary") or {}).get("avg_accuracy"),
            "target": (plan.get("targets") or {}).get("calories")}


@router.post("/generate")
async def generate(body: GeneratePlanIn, user=Depends(get_current_user)):
    profile = serialize(await user_profile(user))
    meals = await load_meals()
    try:
        return planner.generate_plan(profile, meals, days=body.days, strategy=body.strategy,
                                     optimize=body.optimize, meals_per_day=body.meals_per_day)
    except planner.PlanError as e:
        raise HTTPException(422, str(e))


@router.post("/alternatives")
async def alternatives(body: AlternativesIn, user=Depends(get_current_user)):
    profile = serialize(await user_profile(user))
    meals = await load_meals()
    target = body.target_kcal or profile.get("daily_calories_target") or 2000
    try:
        return {"alternatives": planner.alternatives(profile, meals, body.slot, set(body.exclude), float(target))}
    except planner.PlanError as e:
        raise HTTPException(422, str(e))


@router.post("")
async def save(body: SavePlanIn, user=Depends(get_current_user)):
    uid = ObjectId(user["id"])
    if body.activate:
        await _deactivate(uid)
    doc = {"_id": oid(), "user_id": uid, "name": body.name, "plan": body.plan, "is_active": body.activate,
           "activated_on": utcnow().date().isoformat() if body.activate else None, "created_at": utcnow()}
    await db.col("diet_plans").insert_one(doc)
    return serialize(doc)


async def _deactivate(uid):
    for p in await db.col("diet_plans").find({"user_id": uid}).to_list(200):
        if p.get("is_active"):
            await db.col("diet_plans").update_one({"_id": p["_id"]}, {"$set": {"is_active": False}})


@router.get("")
async def list_plans(user=Depends(get_current_user)):
    docs = await db.col("diet_plans").find({"user_id": ObjectId(user["id"])}).sort("created_at", -1).to_list(100)
    return [_summary(d) for d in docs]


async def _owned(plan_id: str, user: dict) -> dict:
    doc = await db.col("diet_plans").find_one({"_id": ObjectId(plan_id)})
    if not doc or str(doc["user_id"]) != user["id"]:
        raise HTTPException(404, "Plan not found")
    return doc


@router.get("/{plan_id}")
async def get_plan(plan_id: str, user=Depends(get_current_user)):
    return serialize(await _owned(plan_id, user))


@router.put("/{plan_id}")
async def update_plan(plan_id: str, body: SavePlanIn, user=Depends(get_current_user)):
    doc = await _owned(plan_id, user)
    await db.col("diet_plans").update_one({"_id": doc["_id"]}, {"$set": {"name": body.name, "plan": body.plan}})
    return serialize(await db.col("diet_plans").find_one({"_id": doc["_id"]}))


@router.post("/{plan_id}/activate")
async def activate(plan_id: str, user=Depends(get_current_user)):
    doc = await _owned(plan_id, user)
    await _deactivate(doc["user_id"])
    await db.col("diet_plans").update_one({"_id": doc["_id"]}, {"$set": {"is_active": True, "activated_on": utcnow().date().isoformat()}})
    return {"ok": True}


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str, user=Depends(get_current_user)):
    doc = await _owned(plan_id, user)
    await db.col("diet_plans").delete_one({"_id": doc["_id"]})
    return {"ok": True}
