from fastapi import APIRouter, HTTPException

from algorithms.nutrition import apply_targets
from auth_utils import create_token, hash_password, verify_password
from db import db, oid, serialize, utcnow
from models.schemas import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


def default_profile(user_id, name: str) -> dict:
    base = {
        "_id": oid(), "user_id": user_id, "name": name, "age": 25, "sex": "other", "height_cm": 170, "weight": 70,
        "target_weight": None, "activity_level": "light", "goal": "balanced", "life_stage": "adult",
        "health_condition": [], "allergies": [], "dietary_restrictions": [], "meals_per_day": 4,
        "workout_split": "full_body", "custom_calories": None, "rl_weights": {}, "onboarded": False,
        "created_at": utcnow(),
    }
    base.update(apply_targets(base))
    return base


def session(user: dict, profile: dict) -> dict:
    token = create_token(str(user["_id"]), user["email"])
    return {"access_token": token, "token_type": "bearer",
            "user": {"id": str(user["_id"]), "email": user["email"], "profile": serialize(profile)}}


@router.post("/register")
async def register(body: UserCreate):
    email = body.email.lower()
    if await db.col("users").find_one({"email": email}):
        raise HTTPException(400, "That email is already registered")
    user = {"_id": oid(), "email": email, "password_hash": hash_password(body.password), "created_at": utcnow()}
    await db.col("users").insert_one(user)
    profile = default_profile(user["_id"], body.name.strip() or "Friend")
    await db.col("profiles").insert_one(profile)
    return session(user, profile)


@router.post("/login")
async def login(body: UserLogin):
    user = await db.col("users").find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    profile = await db.col("profiles").find_one({"user_id": user["_id"]})
    if not profile:
        profile = default_profile(user["_id"], "Friend")
        await db.col("profiles").insert_one(profile)
    return session(user, profile)
