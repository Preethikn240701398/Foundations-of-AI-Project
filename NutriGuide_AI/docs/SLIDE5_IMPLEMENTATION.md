# Slide 5 - Implementation

**How the system is implemented (React + FastAPI + MongoDB)**

| # | Stage | What happens | Where in the code |
|---|-------|--------------|-------------------|
| 1 | **User data collection** | 3-step onboarding wizard collects age, sex, height, weight, activity, goal, allergies, conditions, eating style. Validated by Pydantic, saved to MongoDB. | `frontend/src/pages/Onboarding.jsx`, `components/ProfileForm.jsx`, `backend/models/schemas.py`, `routers/profiles.py` |
| 2 | **BMI / nutritional requirements** | BMI (WHO bands), BMR (Mifflin-St Jeor), TDEE (activity multiplier), goal adjustment with safety floor, macros, fibre, water, sodium. A live preview shows every calculation step. | `backend/algorithms/nutrition.py`, `routers/nutrition.py` |
| 3 | **Knowledge base creation** | Ontology (allergens, diets, 6 conditions, life stages), numeric thresholds that turn data into symbols such as `item(high_gi)`, and a catalogue of 58 meals + foods + workouts. | `backend/algorithms/knowledge_base.py`, `backend/seed.py` |
| 4 | **Rule definition** | 41 IF-THEN production rules stored as readable data, in 7 categories. Variables (`?a`) allow one rule to cover every allergen. | `RULES` in `knowledge_base.py` |
| 5 | **Inference engine** | Forward chaining (recognise-act cycle, conflict resolution, unification, negation-as-failure) and backward chaining (proof trees). Every decision has a trace. | `backend/algorithms/logic.py` |
| 6 | **Meal selection & recommendation** | Engine verdict per meal (recommended / okay / caution / avoid), ranking by rule score + learned preferences + calorie fit, portion scaling. Unsafe meals are removed. | `backend/algorithms/planner.py`, `routers/meals.py` |
| 7 | **Diet plan generation** | CSP solver (backtracking, MRV, forward checking, relaxation ladder), A* and BFS alternatives, simulated-annealing week optimiser, portion calibration, shopping list. | `backend/algorithms/csp.py`, `search.py`, `planner.py`, `routers/diet_plans.py` |
| 8 | **Database / storage** | MongoDB collections: users, profiles, meals, foods, workouts, diet_plans, diary, weights, chat_history, logs. JSON-file fallback when Mongo is not installed. | `backend/db.py` |
| 9 | **User interface** | React (Vite) single-page app: dashboard with calorie ring and macros, diet plan builder, meal explorer, assistant with explainable answers, knowledge-base browser and what-if playground, progress charts, light/dark theme, responsive. | `frontend/src/` |

## One-line summary for the slide
> User data -> BMI/BMR/TDEE -> knowledge base of facts and 41 rules -> forward/backward-chaining inference -> safe, ranked meals -> CSP-generated 7-day plan -> stored in MongoDB -> shown in a React dashboard.

## Syllabus coverage
| Unit | Technique | Where it is used |
|------|-----------|------------------|
| I | Intelligent agent (perceive, decide, act) | `algorithms/agent.py`, assistant |
| I | BFS (uninformed search) | Diet plan > BFS |
| II | A* (informed search) | Diet plan > A* |
| II | Simulated annealing (local search) | Week optimiser |
| II | Search under uncertainty (belief state) | Food scanner |
| III | Constraint satisfaction, backtracking, forward checking | Diet plan > CSP solver |
| III | Minimax, alpha-beta, Monte Carlo Tree Search | AI Lab |
| IV | Propositional + first-order style rules, forward/backward chaining, unification | Inference engine, Assistant, Knowledge base |
| V | Linear regression, k-means, reinforcement-style preference learning | Progress page |
| V | Generative AI (optional Gemini) | `/chatbot/genai-explain` |
