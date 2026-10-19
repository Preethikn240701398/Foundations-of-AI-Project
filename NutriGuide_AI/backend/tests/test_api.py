"""End-to-end tests: run with  `pytest -q`  from the backend folder (uses the in-memory database)."""
import os
import tempfile

os.environ["MEMORY_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_db.json")
os.environ["MONGO_URI"] = "mongodb://127.0.0.1:1"  # unreachable -> forces the in-memory fallback

import pytest
from fastapi.testclient import TestClient

from algorithms import logic
from algorithms.nutrition import compute_requirements
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/auth/register", json={"email": "t@example.com", "password": "secret1", "name": "Tess"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    prof = {"name": "Tess", "age": 30, "sex": "female", "height_cm": 165, "weight": 82, "activity_level": "light",
            "goal": "weight_loss", "life_stage": "adult", "health_condition": ["diabetes"],
            "allergies": ["peanut"], "dietary_restrictions": ["vegetarian"], "meals_per_day": 4,
            "workout_split": "full_body"}
    r = client.put("/profiles/me", json=prof, headers=h)
    assert r.status_code == 200, r.text
    return h


def test_health(client):
    assert client.get("/health").json()["ok"]


def test_bmi_and_requirements():
    r = compute_requirements({"age": 30, "sex": "female", "height_cm": 165, "weight": 82, "activity_level": "light", "goal": "weight_loss"})
    assert r["bmi"] == 30.1 and r["bmi_category"] == "obese"
    assert r["bmr"] == 1540 and r["tdee"] == 2118 and 1500 < r["calories"] < 1900
    low = compute_requirements({"age": 30, "sex": "female", "height_cm": 170, "weight": 45, "goal": "weight_loss"})
    assert low["goal"] == "balanced" and low["warnings"]  # safety rule: no weight-loss when underweight


def test_profile_targets_saved(client, auth):
    p = client.get("/profiles/me", headers=auth).json()
    assert p["onboarded"] and p["daily_calories_target"] == p["requirements"]["calories"]
    assert p["glycemic_target_max"] == 55


def test_engine_rules():
    prof = {"allergies": ["peanut"], "health_condition": ["diabetes"], "dietary_restrictions": ["vegetarian"], "goal": "weight_loss",
            "weight": 82, "height_cm": 165, "age": 30}
    assert logic.evaluate_item(prof, {"name": "x", "calories": 300, "protein": 10, "glycemic_index": 30, "tags": [], "allergens": ["peanut"]})["verdict"] == "avoid"
    assert logic.evaluate_item(prof, {"name": "x", "calories": 300, "protein": 10, "glycemic_index": 80, "tags": [], "allergens": []})["verdict"] == "avoid"
    assert logic.evaluate_item(prof, {"name": "x", "calories": 300, "protein": 10, "glycemic_index": 30, "tags": ["chicken"], "allergens": []})["verdict"] == "avoid"


@pytest.mark.parametrize("strategy", ["csp", "astar", "bfs"])
def test_generate_plan_is_safe(client, auth, strategy):
    r = client.post("/diet-plans/generate", json={"days": 7, "strategy": strategy, "optimize": strategy == "csp"}, headers=auth)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert len(plan["days"]) == 7
    for day in plan["days"]:
        assert len(day["meals"]) == 4
        for m in day["meals"]:
            assert "peanut" not in m["allergens"]
            assert "meat" not in m["tags"] and "chicken" not in m["tags"] and "fish" not in m["tags"]
            assert m["glycemic_index"] <= 55
            assert m["verdict"] != "avoid"
        assert abs(day["totals"]["calories"] - plan["targets"]["calories"]) / plan["targets"]["calories"] < 0.2
    if strategy == "csp":
        assert plan["summary"]["avg_accuracy"] > 90
        assert plan["algorithm"]["annealing"]["cost_after"] <= plan["algorithm"]["annealing"]["cost_before"]


def test_plan_save_dashboard_diary(client, auth):
    plan = client.post("/diet-plans/generate", json={"days": 3}, headers=auth).json()
    saved = client.post("/diet-plans", json={"name": "Test plan", "plan": plan}, headers=auth).json()
    assert saved["is_active"]
    assert any(p["id"] == saved["id"] for p in client.get("/diet-plans", headers=auth).json())
    dash = client.get("/tracker/dashboard", headers=auth).json()
    assert dash["plan_today"]["total_days"] == 3
    m = dash["plan_today"]["meals"][0]
    r = client.post("/tracker/meal", json={"slot": m["slot"], "name": m["name"], "calories": m["calories"], "protein": m["protein"], "carbs": m["carbs"], "fat": m["fat"]}, headers=auth)
    assert r.status_code == 200
    assert client.post("/tracker/water", json={"ml": 500}, headers=auth).json()["water_ml"] == 500
    day = client.get("/tracker/day", headers=auth).json()
    assert day["totals"]["calories"] == m["calories"]
    eid = day["entries"][0]["id"]
    assert client.delete(f"/tracker/entry/{eid}", headers=auth).status_code == 200
    alts = client.post("/diet-plans/alternatives", json={"slot": "Lunch", "exclude": [m["name"]]}, headers=auth).json()["alternatives"]
    assert alts and all(a["verdict"] != "avoid" for a in alts)
    assert client.delete(f"/diet-plans/{saved['id']}", headers=auth).status_code == 200


def test_weights_and_analytics(client, auth):
    for d, w in [("2026-09-01", 83), ("2026-09-15", 82), ("2026-09-29", 81)]:
        assert client.post("/tracker/weight", json={"weight_kg": w, "date": d}, headers=auth).status_code == 200
    a = client.get("/analytics/overview", headers=auth).json()
    assert a["weights"]["slope_per_week"] < 0 and len(a["weights"]["forecast"]) == 4
    assert a["cohort"]["members_count"] >= 1


def test_meals_knowledge_chat(client, auth):
    meals = client.get("/meals", headers=auth).json()
    assert meals["counts"]["avoid"] > 0 and meals["counts"]["recommended"] > 0
    mid = next(m["id"] for m in meals["meals"] if m["verdict"] == "recommended")
    d = client.get(f"/meals/{mid}", headers=auth).json()
    assert d["proof"]["by"].startswith(("M", "G", "N"))
    assert client.post("/meals/feedback", json={"meal_name": d["meal"]["name"], "accepted": True}, headers=auth).json()["rl_weights"]
    inf = client.post("/knowledge/infer", json={"item_name": "Chicken biryani"}, headers=auth).json()
    assert inf["evaluation"]["verdict"] == "avoid" and inf["proof"]
    inf2 = client.post("/knowledge/infer", json={"item_name": "Chicken biryani", "overrides": {"dietary_restrictions": [], "health_condition": [], "allergies": []}}, headers=auth).json()
    assert inf2["evaluation"]["verdict"] != "avoid" or inf2["evaluation"]["reasons"]["reject"] == []
    assert len(client.get("/knowledge/rules", headers=auth).json()["rules"]) >= 30
    for q, action in [("Is chicken biryani okay for me?", "evaluate_food"), ("What is my BMI?", "explain_requirements"),
                      ("Suggest a lunch", "recommend_meal"), ("Make me a weekly plan", "generate_plan")]:
        r = client.post("/chatbot/query", json={"query": q}, headers=auth).json()
        assert r["action"] == action and r["summary"], (q, r)
    assert len(client.get("/chatbot/history", headers=auth).json()) >= 4


def test_workouts_scanner_lab(client, auth):
    w = client.post("/workout-planner/generate", json={"minutes": 40}, headers=auth).json()
    assert len(w["week"]) == 7 and w["summary"]["sessions"] >= 3
    s = client.post("/food-scanner/identify", json={"query": "dal"}, headers=auth).json()
    assert s["candidates"] and "verdict" in s["candidates"][0]
    g = client.post("/ai-lab/game-move", json={"board": ["X", None, None, None, None, None, None, None, None], "engine": "alphabeta"}, headers=auth).json()
    assert g["board"].count("O") == 1


def test_auth_required(client):
    assert client.get("/profiles/me").status_code == 401
    assert client.post("/auth/login", json={"email": "t@example.com", "password": "wrong"}).status_code == 401
