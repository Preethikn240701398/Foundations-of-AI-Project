"""
Unit I - Intelligent agent wrapper.

NutriGuide is a goal-based agent: it perceives the user's profile and the latest request,
decides which capability to use, and acts by calling the matching algorithm module.
"""
from __future__ import annotations

from algorithms import logic, planner
from algorithms.nutrition import compute_requirements


class NutriAgent:
    def __init__(self, profile: dict):
        self.profile = profile
        self.percepts: list[dict] = []

    def perceive(self, event: dict) -> None:
        self.percepts.append(event)

    def decide(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ("plan", "week", "menu", "diet chart")):
            return "generate_plan"
        if any(w in t for w in ("bmi", "calorie", "kcal", "protein", "macro", "water", "bmr", "tdee")):
            return "explain_requirements"
        if any(w in t for w in ("suggest", "recommend", "what should i eat", "ideas", "hungry")):
            return "recommend_meal"
        if any(w in t for w in ("workout", "exercise", "gym", "train")):
            return "advise_workout"
        return "evaluate_food"

    def act(self, action: str, **kw):
        if action == "explain_requirements":
            return compute_requirements(self.profile)
        if action == "recommend_meal":
            return planner.rank_catalogue(self.profile, kw.get("meals", []))
        if action == "evaluate_food":
            return logic.evaluate_item(self.profile, kw["item"]) if kw.get("item") else None
        if action == "generate_plan":
            return planner.generate_plan(self.profile, kw.get("meals", []), days=kw.get("days", 7))
        return None
