from bson import ObjectId
from fastapi import APIRouter, Depends

from algorithms import logic
from algorithms.search import rank_uncertain
from auth_utils import get_current_user
from db import db, oid, serialize, utcnow
from models.schemas import ScanIn
from routers.common import load_foods, load_meals
from routers.profiles import user_profile

router = APIRouter(prefix="/food-scanner", tags=["food-scanner"])


@router.post("/identify")
async def identify(body: ScanIn, user=Depends(get_current_user)):
    """Partially-observable search: rank candidate foods by confidence and judge each for this user."""
    profile = serialize(await user_profile(user))
    universe = await load_foods() + await load_meals()
    result = rank_uncertain(universe, body.food_name or body.query)
    facts = logic.user_facts(profile)
    for c in result["candidates"]:
        ev = logic.evaluate_item(profile, c, facts)
        c["verdict"] = ev["verdict"]
        c["why"] = [r["text"] for r in (ev["reasons"]["reject"] + ev["reasons"]["caution"] + ev["reasons"]["prefer"])[:3]]
    if body.confirm and result["candidates"]:
        chosen = result["candidates"][0]
        await db.col("logs").insert_one({"_id": oid(), "user_id": ObjectId(user["id"]), "type": "scan",
                                          "item": chosen["name"], "date": utcnow().date().isoformat(),
                                          "created_at": utcnow()})
        result["confirmed"] = chosen
    return result
