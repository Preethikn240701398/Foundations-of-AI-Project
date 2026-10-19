from fastapi import APIRouter, Depends

from algorithms.nutrition import ACTIVITY_LEVELS, GOALS, apply_targets, compute_requirements
from auth_utils import get_current_user
from algorithms import knowledge_base as kb
from models.schemas import ProfileIn
from routers.profiles import user_profile

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/options")
async def options():
    return {
        "activity_levels": [{"id": k, **v} for k, v in ACTIVITY_LEVELS.items()],
        "goals": [{"id": k, "label": v["label"]} for k, v in GOALS.items()],
        "conditions": [{"id": k, "label": v["label"], "summary": v["summary"]} for k, v in kb.CONDITIONS.items()],
        "allergens": kb.ALLERGENS,
        "diets": [{"id": k, "summary": v} for k, v in kb.DIETS.items()],
        "life_stages": [{"id": k, "label": v} for k, v in kb.LIFE_STAGES.items()],
    }


@router.post("/preview")
async def preview(body: ProfileIn):
    """Live calculation for the onboarding wizard - nothing is saved."""
    data = body.model_dump()
    if isinstance(data["health_condition"], list):
        data["health_condition"] = ",".join(data["health_condition"])
    req = compute_requirements(data)
    if data.get("custom_calories"):
        req["calories"] = data["custom_calories"]
    return req


@router.get("/requirements")
async def requirements(user=Depends(get_current_user)):
    return compute_requirements(await user_profile(user))
