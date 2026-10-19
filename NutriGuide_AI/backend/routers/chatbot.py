from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
import httpx

from algorithms import logic, planner
from algorithms.agent import NutriAgent
from algorithms.nutrition import compute_requirements
from auth_utils import get_current_user
from config import settings
from db import db, oid, serialize, utcnow
from models.schemas import ChatQueryIn, GenAIIn
from routers.common import find_item, find_in_text, load_foods, load_meals
from routers.profiles import user_profile

router = APIRouter(prefix="/chatbot", tags=["assistant"])

VERDICT_TEXT = {
    "recommended": "is a good fit for you",
    "neutral": "is acceptable for you",
    "caution": "is best eaten occasionally",
    "avoid": "is not suitable for you",
}


def _brief(m: dict) -> dict:
    return {k: m.get(k) for k in ("id", "name", "emoji", "calories", "protein", "carbs", "fat", "meal_type",
                                   "verdict", "why", "glycemic_index")}


@router.post("/query")
async def query(body: ChatQueryIn, user=Depends(get_current_user)):
    profile = serialize(await user_profile(user))
    meals, foods = await load_meals(), await load_foods()
    agent = NutriAgent(profile)
    agent.perceive({"query": body.query})
    action = agent.decide(body.query)
    item = find_item(body.food_name, meals, foods) if body.food_name else find_in_text(body.query, meals, foods)
    if item and action in {"evaluate_food", "recommend_meal"} and not any(
            w in body.query.lower() for w in ("suggest", "recommend", "ideas")):
        action = "evaluate_food"

    q = body.query.lower()
    resp: dict = {"action": action, "items": [], "trace": None, "proof": None, "link": None, "item": None,
                  "requirements": None}

    if action == "explain_requirements":
        r = compute_requirements(profile)
        resp["summary"] = (
            f"Your BMI is {r['bmi']} ({r['bmi_label']}). Using the Mifflin-St Jeor equation your BMR is {r['bmr']} kcal, "
            f"and with your activity level your maintenance (TDEE) is {r['tdee']} kcal. For your goal I recommend "
            f"{r['calories']} kcal a day: {r['protein_g']} g protein, {r['carbs_g']} g carbs, {r['fat_g']} g fat, "
            f"{r['fiber_g']} g fibre and about {r['water_ml'] / 1000:.1f} L of water.")
        resp["requirements"] = r
    elif action == "recommend_meal":
        slot = next((s for s in ("Breakfast", "Lunch", "Dinner", "Snack") if s.lower() in q), None)
        ranked = [m for m in planner.rank_catalogue(profile, meals) if m["verdict"] != "avoid"]
        if slot:
            ranked = [m for m in ranked if slot in m["meal_type"]]
        ranked.sort(key=lambda m: -m["match"])
        resp["items"] = [_brief(m) for m in ranked[:4]]
        resp["summary"] = (f"Here are my top {slot.lower() if slot else 'meal'} picks. I removed anything that conflicts "
                           f"with your allergies, diet or health rules, then ranked the rest by how well they match you.")
    elif action == "generate_plan":
        resp["summary"] = ("I can build a complete 7-day plan using constraint solving, then refine the week with "
                           "simulated annealing. Open the Diet Plan page and press Generate.")
        resp["link"] = {"to": "/app/plan", "label": "Open Diet Plan"}
    elif action == "advise_workout":
        r = compute_requirements(profile)
        resp["summary"] = (f"Your current split is {str(profile.get('workout_split')).replace('_', ' ')}. "
                           f"Aim for {r['protein_g']} g of protein daily and eat a carb-and-protein meal within two hours "
                           f"of training. Open the Workouts page for a weekly schedule.")
        resp["link"] = {"to": "/app/workouts", "label": "Open Workouts"}
    elif item:
        ev = logic.evaluate_item(profile, item)
        reasons = (ev["reasons"]["reject"] + ev["reasons"]["caution"] + ev["reasons"]["prefer"])[:3]
        why = " ".join(r["text"] for r in reasons) or "No rule in the knowledge base objects to it."
        resp["summary"] = f"{item['name']} {VERDICT_TEXT[ev['verdict']]}. {why}"
        resp["item"] = {k: item.get(k) for k in ("name", "emoji", "calories", "protein", "carbs", "fat", "glycemic_index", "tags")}
        resp["item"]["verdict"] = ev["verdict"]
        resp["trace"] = {"facts": ev["facts"], "derived": ev["derived"], "fired": ev["fired"]}
        resp["proof"] = logic.prove_verdict(ev)
    else:
        resp["summary"] = ("I can check any food or meal against your allergies, diet, health conditions and goal. "
                           "Try: 'Is chicken biryani okay for me?', 'Suggest a breakfast', or 'What is my BMI?'")
        resp["items"] = []

    doc = {"_id": oid(), "user_id": ObjectId(user["id"]), "query": body.query, "response": resp,
           "created_at": utcnow()}
    await db.col("chat_history").insert_one(doc)
    return {"id": str(doc["_id"]), "query": body.query, **resp}


@router.get("/history")
async def history(user=Depends(get_current_user)):
    docs = await db.col("chat_history").find({"user_id": ObjectId(user["id"])}).sort("created_at", -1).limit(20).to_list(20)
    return [{"id": str(d["_id"]), "query": d["query"], **d["response"]} for d in reversed(docs)]


@router.delete("/history")
async def clear_history(user=Depends(get_current_user)):
    await db.col("chat_history").delete_many({"user_id": ObjectId(user["id"])})
    return {"ok": True}


@router.post("/genai-explain")
async def genai_explain(body: GenAIIn, user=Depends(get_current_user)):
    profile = serialize(await user_profile(user))
    r = compute_requirements(profile)
    summary = (f"age {profile.get('age')}, BMI {r['bmi']}, goal {r['goal']}, target {r['calories']} kcal, "
               f"allergies {profile.get('allergies') or 'none'}, conditions {profile.get('health_condition') or 'none'}")
    if not settings.gemini_api_key:
        return {"source": "logic_fallback",
                "text": f"{body.topic}: for someone with {summary}, keep meals close to your calorie target, "
                        f"avoid anything the knowledge base flags, and favour whole foods. This is educational, not medical advice."}
    prompt = (f"You are NutriGuide AI, a careful nutrition coach. User: {summary}. Topic: {body.topic}. "
              f"Context: {body.context}. Answer in under 120 words. Not medical advice.")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
           f"?key={settings.gemini_api_key}")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            res.raise_for_status()
        return {"source": "gemini", "text": res.json()["candidates"][0]["content"]["parts"][0]["text"]}
    except Exception as exc:  # network / quota errors should not break the page
        raise HTTPException(502, f"GenAI service unavailable: {exc}")
