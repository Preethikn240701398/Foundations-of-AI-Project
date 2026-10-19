from fastapi import APIRouter, Depends

from algorithms.nutrition import compute_requirements
from auth_utils import get_current_user
from db import serialize
from models.schemas import WorkoutGenerateIn
from routers.profiles import user_profile
from seed import all_serialized

router = APIRouter(prefix="/workout-planner", tags=["workouts"])

SCHEDULES = {
    "full_body": ["full_body", "rest", "cardio", "full_body", "rest", "full_body", "rest"],
    "upper_lower": ["upper", "lower", "rest", "upper", "lower", "cardio", "rest"],
    "push_pull": ["push", "pull", "lower", "rest", "push", "pull", "cardio"],
}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _pick_split(profile: dict, requested: str | None) -> str:
    split = (requested or profile.get("workout_split") or "").lower()
    if split in SCHEDULES:
        return split
    return {"sedentary": "full_body", "light": "full_body", "moderate": "upper_lower",
            "active": "push_pull", "athlete": "push_pull"}.get(profile.get("activity_level"), "full_body")


@router.get("/catalog")
async def catalog(user=Depends(get_current_user)):
    return await all_serialized("workouts")


@router.post("/generate")
async def generate(body: WorkoutGenerateIn | None = None, user=Depends(get_current_user)):
    body = body or WorkoutGenerateIn()
    profile = serialize(await user_profile(user))
    req = compute_requirements(profile)
    split = _pick_split(profile, body.split_type)
    workouts = await all_serialized("workouts")
    by_type = {w["split_type"]: w for w in workouts}
    template = list(SCHEDULES[split])
    if req["goal"] == "weight_loss" and "rest" in template:  # one extra cardio day for fat loss
        template[len(template) - 1 - template[::-1].index("rest")] = "cardio"

    week, burn_total, sessions = [], 0, 0
    for day, kind in zip(DAYS, template):
        if kind == "rest":
            week.append({"day": day, "type": "rest", "title": "Rest & recovery", "minutes": 20, "calories": 80,
                         "exercises": [{"name": "Easy walk", "sets": 1, "reps": "20 min"},
                                       {"name": "Mobility flow", "sets": 1, "reps": "10 min"}]})
            continue
        w = by_type.get(kind) or workouts[0]
        burn = int(round(w["calories"] * body.minutes / 45 * max(profile.get("weight", 70), 40) / 70))
        sessions += 1
        burn_total += burn
        week.append({"day": day, "type": kind, "title": w["name"], "minutes": body.minutes, "calories": burn,
                     "exercises": w["exercises"], "tags": w.get("tags", [])})
    return {"split": split, "minutes": body.minutes, "week": week,
            "summary": {"sessions": sessions, "weekly_burn": burn_total, "protein_target": req["protein_g"]},
            "algorithm": "rule-based weekly schedule with recovery constraints"}
