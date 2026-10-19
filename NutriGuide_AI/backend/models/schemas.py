"""Pydantic request / response models."""
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = "Friend"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    """Step 1 - user data collection."""
    name: str = "Friend"
    age: int = Field(25, ge=10, le=100)
    sex: str = "other"                      # male | female | other
    height_cm: float = Field(170, ge=100, le=230)
    weight: float = Field(70, ge=25, le=300)
    target_weight: float | None = None
    activity_level: str = "light"           # sedentary | light | moderate | active | athlete
    goal: str = "balanced"                  # weight_loss | balanced | muscle_gain | weight_gain
    life_stage: str = "adult"               # adult | teen | senior | pregnancy | lactation
    health_condition: list[str] | str = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    meals_per_day: int = Field(4, ge=3, le=4)
    workout_split: str = "full_body"
    custom_calories: int | None = Field(None, ge=1000, le=6000)


class GeneratePlanIn(BaseModel):
    days: int = Field(7, ge=1, le=14)
    strategy: str = "csp"                   # csp | astar | bfs
    optimize: bool = True
    meals_per_day: int | None = None


class AlternativesIn(BaseModel):
    slot: str
    exclude: list[str] = Field(default_factory=list)
    target_kcal: float | None = None


class SavePlanIn(BaseModel):
    name: str = "My diet plan"
    plan: dict
    activate: bool = True


class FeedbackIn(BaseModel):
    meal_name: str
    tags: list[str] = Field(default_factory=list)
    accepted: bool = True


class DiaryMealIn(BaseModel):
    date: str | None = None
    slot: str = "Snack"
    name: str
    calories: float
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    portion: float = 1.0
    source: str = "manual"


class WaterIn(BaseModel):
    ml: int = Field(250, ge=50, le=2000)
    date: str | None = None


class WeightIn(BaseModel):
    weight_kg: float = Field(ge=25, le=300)
    date: str | None = None


class ChatQueryIn(BaseModel):
    query: str
    food_name: str | None = None


class InferIn(BaseModel):
    item_name: str
    overrides: dict = Field(default_factory=dict)


class ScanIn(BaseModel):
    query: str = ""
    confirm: bool = False
    food_name: str | None = None


class GenAIIn(BaseModel):
    topic: str
    context: str = ""


class WorkoutGenerateIn(BaseModel):
    split_type: str | None = None
    minutes: int = Field(45, ge=15, le=120)


class GameMoveIn(BaseModel):
    board: list[str | None] = Field(default_factory=lambda: [None] * 9)
    engine: str = "alphabeta"
