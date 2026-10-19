from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from algorithms.nutrition import apply_targets, compute_requirements
from auth_utils import get_current_user
from db import db, serialize
from models.schemas import ProfileIn

router = APIRouter(prefix="/profiles", tags=["profiles"])


async def user_profile(user: dict) -> dict:
    profile = await db.col("profiles").find_one({"user_id": ObjectId(user["id"])})
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


def with_requirements(profile: dict) -> dict:
    data = serialize(profile)
    data["requirements"] = compute_requirements(profile)
    return data


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return with_requirements(await user_profile(user))


@router.put("/me")
async def update_me(body: ProfileIn, user=Depends(get_current_user)):
    profile = await user_profile(user)
    fields = body.model_dump()
    if isinstance(fields["health_condition"], str):
        fields["health_condition"] = [c.strip() for c in fields["health_condition"].split(",") if c.strip()]
    fields["health_condition"] = [c for c in fields["health_condition"] if c.lower() not in {"none", ""}]
    fields["allergies"] = [a.strip().lower() for a in fields["allergies"] if a.strip()]
    merged = {**profile, **fields}
    targets = apply_targets(merged)
    if fields.get("custom_calories"):
        targets["daily_calories_target"] = int(fields["custom_calories"])
    await db.col("profiles").update_one({"_id": profile["_id"]}, {"$set": {**fields, **targets, "onboarded": True}})
    return with_requirements(await db.col("profiles").find_one({"_id": profile["_id"]}))
