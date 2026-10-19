from collections import defaultdict
from datetime import date, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends

from algorithms.ml import kmeans, linear_regression_trend, zscore
from algorithms.nutrition import compute_requirements
from auth_utils import get_current_user
from db import db
from routers.profiles import user_profile

router = APIRouter(prefix="/analytics", tags=["analytics"])

COHORT = [  # anonymised sample cohort so clustering is meaningful with few real users
    {"label": "Active lifter", "age": 28, "calories": 2800, "protein": 150, "bmi": 24.5, "goal": "muscle_gain"},
    {"label": "Busy professional", "age": 35, "calories": 2100, "protein": 95, "bmi": 26.8, "goal": "balanced"},
    {"label": "Weight-loss starter", "age": 42, "calories": 1700, "protein": 110, "bmi": 31.0, "goal": "weight_loss"},
    {"label": "Student", "age": 21, "calories": 2300, "protein": 90, "bmi": 22.0, "goal": "balanced"},
    {"label": "Senior wellness", "age": 66, "calories": 1750, "protein": 85, "bmi": 27.0, "goal": "balanced"},
    {"label": "Endurance runner", "age": 31, "calories": 2600, "protein": 120, "bmi": 21.5, "goal": "balanced"},
    {"label": "Post-natal mum", "age": 33, "calories": 2200, "protein": 100, "bmi": 25.2, "goal": "balanced"},
    {"label": "Lean bulk", "age": 24, "calories": 3000, "protein": 160, "bmi": 22.8, "goal": "weight_gain"},
]


@router.get("/overview")
async def overview(user=Depends(get_current_user)):
    uid = ObjectId(user["id"])
    profile = await user_profile(user)
    req = compute_requirements(profile)
    today = date.today()

    # ---- supervised learning: weight regression + forecast --------------
    w = await db.col("weights").find({"user_id": uid}).sort("date", 1).to_list(1000)
    weight_series = [{"date": x["date"], "weight": x["weight_kg"]} for x in w]
    forecast, eta_weeks, slope_week = [], None, 0.0
    if len(w) >= 2:
        d0 = date.fromisoformat(w[0]["date"])
        xs = [(date.fromisoformat(x["date"]) - d0).days for x in w]
        slope, intercept = linear_regression_trend(xs, [x["weight_kg"] for x in w])
        slope_week = round(slope * 7, 2)
        last_x = xs[-1]
        for i in range(1, 5):
            fx = last_x + 7 * i
            forecast.append({"date": (d0 + timedelta(days=fx)).isoformat(), "weight": round(slope * fx + intercept, 1)})
        tw = profile.get("target_weight")
        if tw and abs(slope) > 1e-4:
            weeks = (float(tw) - w[-1]["weight_kg"]) / (slope * 7)
            eta_weeks = round(weeks, 1) if weeks > 0 else None

    # ---- calorie intake vs target (last 14 days) -------------------------
    diary = await db.col("diary").find({"user_id": uid, "type": "meal"}).to_list(5000)
    per_day: dict[str, dict] = defaultdict(lambda: {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
    for e in diary:
        for k in per_day.default_factory().keys():
            per_day[e["date"]][k] += float(e.get(k) or 0)
    target = req["calories"]
    intake = []
    for i in range(13, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        intake.append({"date": d, "calories": int(per_day[d]["calories"]) if d in per_day else 0, "target": target})
    logged_days = [x for x in intake if x["calories"] > 0]
    adherence = round(100 * sum(1 for x in logged_days if abs(x["calories"] - target) <= 0.15 * target)
                      / len(logged_days)) if logged_days else None

    last7 = [per_day[(today - timedelta(days=i)).isoformat()] for i in range(7) if (today - timedelta(days=i)).isoformat() in per_day]
    macro_avg = None
    if last7:
        n = len(last7)
        macro_avg = {k: round(sum(d[k] for d in last7) / n) for k in ("calories", "protein", "carbs", "fat")}

    # ---- reinforcement learning: learned preferences ---------------------
    rl = profile.get("rl_weights") or {}
    prefs = sorted(({"tag": k, "weight": v} for k, v in rl.items()), key=lambda x: -x["weight"])

    # ---- unsupervised learning: k-means cohort ----------------------------
    me = {"label": "You", "age": profile.get("age") or 25, "calories": req["calories"], "protein": req["protein_g"],
          "bmi": req["bmi"], "goal": req["goal"]}
    people = COHORT + [me]
    X = zscore([[p["age"], p["calories"], p["protein"], p["bmi"]] for p in people])
    labels, centroids = kmeans(X.tolist(), k=3)
    mine = labels[-1]
    cluster_members = [{**p, "cluster": int(labels[i])} for i, p in enumerate(people[:-1]) if labels[i] == mine]
    real_profiles = await db.col("profiles").count_documents({})
    return {
        "weights": {"series": weight_series, "forecast": forecast, "slope_per_week": slope_week, "eta_weeks": eta_weeks,
                    "target_weight": profile.get("target_weight"), "algorithm": "least-squares linear regression"},
        "intake": {"series": intake, "adherence": adherence, "macro_avg": macro_avg},
        "preferences": {"top": prefs[:6], "bottom": list(reversed(prefs[-4:])) if len(prefs) > 6 else [],
                        "algorithm": "reinforcement-style weight update (+1 accept / -1 reject)"},
        "cohort": {"cluster": int(mine), "members": cluster_members, "members_count": len(cluster_members),
                   "real_members": real_profiles, "algorithm": "k-means (k=3, z-scored features)"},
    }
