from datetime import date, datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from algorithms.nutrition import apply_targets, compute_requirements
from auth_utils import get_current_user
from db import db, oid, serialize, utcnow
from models.schemas import DiaryMealIn, WaterIn, WeightIn
from routers.profiles import user_profile

router = APIRouter(prefix="/tracker", tags=["tracker"])

MACROS = ["calories", "protein", "carbs", "fat", "fiber"]


def _today() -> str:
    return date.today().isoformat()


def _totals(entries: list[dict]) -> dict:
    meals = [e for e in entries if e.get("type") == "meal"]
    t = {k: round(sum(float(e.get(k) or 0) for e in meals), 1) for k in MACROS}
    t["calories"] = int(t["calories"])
    return t


async def _day(uid, day: str) -> dict:
    entries = await db.col("diary").find({"user_id": uid, "date": day}).sort("created_at", 1).to_list(200)
    water = sum(int(e.get("ml") or 0) for e in entries if e.get("type") == "water")
    meals = [serialize(e) for e in entries if e.get("type") == "meal"]
    return {"date": day, "entries": meals, "totals": _totals(entries), "water_ml": water}


@router.get("/day")
async def day(date: str | None = None, user=Depends(get_current_user)):
    return await _day(ObjectId(user["id"]), date or _today())


@router.post("/meal")
async def add_meal(body: DiaryMealIn, user=Depends(get_current_user)):
    doc = {"_id": oid(), "user_id": ObjectId(user["id"]), "type": "meal", "date": body.date or _today(),
           **body.model_dump(exclude={"date"}), "created_at": utcnow()}
    await db.col("diary").insert_one(doc)
    return serialize(doc)


@router.delete("/entry/{entry_id}")
async def delete_entry(entry_id: str, user=Depends(get_current_user)):
    doc = await db.col("diary").find_one({"_id": ObjectId(entry_id)})
    if not doc or str(doc["user_id"]) != user["id"]:
        raise HTTPException(404, "Entry not found")
    await db.col("diary").delete_one({"_id": doc["_id"]})
    return {"ok": True}


@router.post("/water")
async def add_water(body: WaterIn, user=Depends(get_current_user)):
    await db.col("diary").insert_one({"_id": oid(), "user_id": ObjectId(user["id"]), "type": "water",
                                      "date": body.date or _today(), "ml": body.ml, "created_at": utcnow()})
    return await _day(ObjectId(user["id"]), body.date or _today())


@router.post("/weight")
async def log_weight(body: WeightIn, user=Depends(get_current_user)):
    """Store a weigh-in and refresh BMI / calorie / macro targets from the new weight."""
    uid = ObjectId(user["id"])
    day_ = body.date or _today()
    existing = await db.col("weights").find_one({"user_id": uid, "date": day_})
    if existing:
        await db.col("weights").update_one({"_id": existing["_id"]}, {"$set": {"weight_kg": body.weight_kg}})
    else:
        await db.col("weights").insert_one({"_id": oid(), "user_id": uid, "date": day_,
                                            "weight_kg": body.weight_kg, "created_at": utcnow()})
    profile = await user_profile(user)
    newest = await db.col("weights").find({"user_id": uid}).sort("date", -1).limit(1).to_list(1)
    if newest and newest[0]["date"] == day_:
        merged = {**profile, "weight": body.weight_kg}
        targets = apply_targets(merged)
        if profile.get("custom_calories"):
            targets["daily_calories_target"] = int(profile["custom_calories"])
        await db.col("profiles").update_one({"_id": profile["_id"]}, {"$set": {"weight": body.weight_kg, **targets}})
    updated = await user_profile(user)
    return {"ok": True, "requirements": compute_requirements(updated), "weight": body.weight_kg}


@router.get("/weights")
async def weights(user=Depends(get_current_user)):
    docs = await db.col("weights").find({"user_id": ObjectId(user["id"])}).sort("date", 1).to_list(1000)
    return [{"date": d["date"], "weight_kg": d["weight_kg"]} for d in docs]


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    uid = ObjectId(user["id"])
    profile = await user_profile(user)
    today = _today()
    day_ = await _day(uid, today)
    plan_doc = None
    for p in await db.col("diet_plans").find({"user_id": uid}).to_list(100):
        if p.get("is_active"):
            plan_doc = p
    plan_today = None
    if plan_doc:
        days = (plan_doc.get("plan") or {}).get("days") or []
        if days:
            started = date.fromisoformat(plan_doc.get("activated_on") or today)
            idx = (date.today() - started).days % len(days)
            plan_today = {"plan_id": str(plan_doc["_id"]), "plan_name": plan_doc.get("name"), "day_number": idx + 1,
                          "total_days": len(days), **{k: days[idx][k] for k in ("meals", "totals", "weekday")}}
    # logging streak
    streak, cursor = 0, date.today()
    logged = {e["date"] for e in await db.col("diary").find({"user_id": uid, "type": "meal"}).to_list(2000)}
    if today not in logged:
        cursor -= timedelta(days=1)
    while cursor.isoformat() in logged:
        streak += 1
        cursor -= timedelta(days=1)
    w = await db.col("weights").find({"user_id": uid}).sort("date", 1).to_list(60)
    return {
        "profile": serialize(profile), "requirements": compute_requirements(profile), "today": day_,
        "plan_today": plan_today, "streak": streak,
        "weights": [{"date": x["date"], "weight_kg": x["weight_kg"]} for x in w][-30:],
    }
