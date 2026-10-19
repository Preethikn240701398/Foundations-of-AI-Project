# NutriGuide AI v2

A knowledge-based nutrition assistant. It collects your data, calculates BMI and daily requirements, applies **41 expert rules** with a **forward/backward-chaining inference engine**, and builds a safe **7-day diet plan** with a **constraint solver**.

**Stack:** React (Vite) · FastAPI (Python) · MongoDB (optional, JSON fallback built in)

> Educational project. Nutrition output is general information, not medical advice.

## Quick start

You need **Python 3.10+** and **Node 18+**. MongoDB is optional.

```bash
# 1. backend  (http://127.0.0.1:8000, API docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. frontend (http://localhost:5173)  - open a second terminal
cd frontend
npm install
npm run dev
```

Windows shortcut: double-click `run_backend.bat`, then `run_frontend.bat`. macOS/Linux: `./run_backend.sh` and `./run_frontend.sh`.

**Database:** if MongoDB is running on `localhost:27017` the app uses it automatically (`docker compose up -d` starts one). Otherwise it stores data in `backend/data/memory_db.json`, so everything still works. `GET /health` shows which one is active.

Copy `backend/.env.example` to `backend/.env` to change the Mongo URL, JWT secret or add a Gemini key (optional).

## Try this
1. Register, then complete the 3-step onboarding. Watch BMI/BMR/TDEE update live.
2. Choose *Type 2 diabetes + peanut allergy + vegetarian*, open **Diet plan** and press **Generate**. Every meal respects all three.
3. Open **Assistant** and ask *"Is chicken biryani okay for me?"*. Expand **How I decided** to see the rules that fired.
4. Open **Knowledge base > Inference playground** and toggle conditions to see verdicts change.
5. On the plan page switch **CSP solver / A\* / BFS** and compare the *How it was solved* tab.

## Tests
```bash
cd backend && pytest -q        # 12 end-to-end tests, uses an in-memory database
```

## Project layout
```
backend/
  main.py  config.py  db.py  auth_utils.py  seed.py
  algorithms/        pure Python, no web/database imports
    nutrition.py       BMI, BMR, TDEE, macros
    knowledge_base.py  ontology, thresholds, 41 rules
    logic.py           inference engine (forward + backward chaining)
    planner.py         meal ranking and diet-plan generation
    csp.py             backtracking CSP solver
    search.py          BFS, A*, simulated annealing, belief-state ranking
    ml.py              regression, k-means, preference learning
    games.py           minimax, alpha-beta, MCTS
    agent.py           goal-based agent wrapper
  routers/           one FastAPI router per feature
  tests/test_api.py
frontend/src/
  pages/             Dashboard, DietPlan, Meals, Workouts, Assistant, FoodScanner,
                     KnowledgeBase, Progress, AILab, Profile, Onboarding, Landing, Auth
  components/        Layout, ProfileForm, MealCard, ReasoningTrace, ui kit
docs/SLIDE5_IMPLEMENTATION.md   slide text + syllabus mapping
```

## Main API endpoints
| Area | Endpoints |
|------|-----------|
| Auth / profile | `POST /auth/register`, `POST /auth/login`, `GET/PUT /profiles/me` |
| Requirements | `POST /nutrition/preview`, `GET /nutrition/requirements` |
| Meals | `GET /meals`, `GET /meals/{id}`, `POST /meals/feedback` |
| Diet plans | `POST /diet-plans/generate`, `/alternatives`, `POST /diet-plans`, `GET/PUT/DELETE /diet-plans/{id}` |
| Tracking | `GET /tracker/dashboard`, `POST /tracker/meal`, `/water`, `/weight` |
| Knowledge | `GET /knowledge/rules`, `/overview`, `/foods`, `POST /knowledge/infer` |
| Assistant | `POST /chatbot/query`, `GET /chatbot/history` |
| Insights | `GET /analytics/overview`, `POST /workout-planner/generate`, `POST /ai-lab/game-move` |

Interactive docs: http://127.0.0.1:8000/docs

## Adding a rule
Open `backend/algorithms/knowledge_base.py` and append to `RULES`:
```python
{"id": "M11", "cat": "medical", "if": "condition(hypertension) AND item(fried)",
 "then": "caution", "type": "caution", "weight": 30, "text": "Fried food raises blood pressure."}
```
Restart the backend. The rule appears in the Knowledge base page and is used by every recommendation.

## Upgrading from the previous version
Meals, foods and workouts are re-seeded automatically (seed version 2). User accounts, profiles and logs are never deleted. Existing profiles work, but open **My profile** once to add age, height and activity level so the new calculator has real inputs.
