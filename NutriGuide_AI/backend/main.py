from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import db
from routers import (ai_lab, analytics, auth, chatbot, diet_plans, food_scanner, knowledge, meals, nutrition,
                     profiles, tracker, workout_planner)
from seed import seed_if_needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await seed_if_needed()
    db.flush()
    yield
    db.flush()


app = FastAPI(title="NutriGuide AI", version="2.0.0",
              description="Knowledge-based nutrition system: rules + inference engine + CSP/search planner", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def persist_after_writes(request: Request, call_next):
    response = await call_next(request)
    if request.method != "GET":
        db.flush()  # no-op when MongoDB is in use
    return response


for r in (auth, profiles, nutrition, meals, knowledge, diet_plans, tracker, analytics, chatbot, food_scanner,
          workout_planner, ai_lab):
    app.include_router(r.router)


@app.get("/health")
async def health():
    return {"ok": True, "db": db.mode, "version": app.version}
