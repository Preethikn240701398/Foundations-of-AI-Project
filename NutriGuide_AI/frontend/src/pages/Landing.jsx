import { Link } from "react-router-dom";
import { Leaf, Calculator, Library, ListChecks, Cpu, Salad, CalendarDays, Database, LayoutDashboard, ClipboardList, ShieldCheck, Brain } from "lucide-react";
import { Ring } from "../components/ui";

const STEPS = [
  [ClipboardList, "Collect data", "Age, body measures, goal, allergies and health conditions."],
  [Calculator, "Calculate needs", "BMI, BMR, TDEE, calories and macros from proven formulas."],
  [Library, "Knowledge base", "Foods, conditions and thresholds stored as structured facts."],
  [ListChecks, "Rules", "40+ IF-THEN rules written as readable, editable data."],
  [Cpu, "Inference engine", "Forward and backward chaining decide what is safe."],
  [Salad, "Select meals", "Meals are ranked and filtered for you."],
  [CalendarDays, "Generate plan", "A constraint solver builds a balanced week."],
  [Database, "Store", "MongoDB keeps profiles, plans, diary and progress."],
  [LayoutDashboard, "Dashboard", "Track calories, macros, water and weight."],
];

export default function Landing() {
  return (
    <div>
      <nav className="land-nav">
        <div className="brand" style={{ padding: 0 }}><span className="brand-mark"><Leaf size={19} /></span>NutriGuide AI</div>
        <div className="row"><Link to="/login" className="btn ghost">Log in</Link><Link to="/register" className="btn">Get started</Link></div>
      </nav>
      <header className="hero">
        <div>
          <div className="eyebrow">Knowledge-based nutrition system</div>
          <h1>Personal diet plans you can <span>trust and understand</span></h1>
          <p className="lead">NutriGuide AI calculates your daily needs, applies expert nutrition rules with an inference engine, and builds a safe 7-day meal plan around your allergies, health and goals.</p>
          <div className="row wrap"><Link to="/register" className="btn lg">Build my plan</Link><Link to="/login" className="btn secondary lg">I have an account</Link></div>
          <div className="row gap-16 mt-24 small muted wrap"><span className="row gap-6"><ShieldCheck size={16} /> Safety-first rules</span><span className="row gap-6"><Brain size={16} /> Explainable decisions</span></div>
        </div>
        <div className="hero-card">
          <div className="row between"><div><div className="muted small">Today</div><h3>Sample dashboard</h3></div><span className="badge good">On track</span></div>
          <div className="row gap-20 mt-16" style={{ justifyContent: "center" }}>
            <Ring value={1380} max={1800} size={150}><b>1,380</b><span className="tiny muted">of 1,800 kcal</span></Ring>
            <div className="col grow" style={{ gap: 12 }}>
              {[["Protein", 82, 110, "var(--protein)"], ["Carbs", 150, 200, "var(--carbs)"], ["Fat", 48, 60, "var(--fat)"]].map(([l, v, t, c]) => (
                <div key={l}><div className="row between tiny"><b>{l}</b><span className="muted">{v}/{t}g</span></div><div className="bar mt-4"><i style={{ width: `${(v / t) * 100}%`, background: c }} /></div></div>
              ))}
            </div>
          </div>
          <div className="card soft mt-16"><div className="row gap-12"><span style={{ fontSize: 26 }}>🥗</span><div><div className="bold small">Chickpea &amp; quinoa power salad</div><div className="tiny muted"><b>M03</b> Low glycaemic index supports your blood-sugar goal.</div></div></div></div>
        </div>
      </header>
      <section className="section">
        <div className="eyebrow">How it works</div>
        <h2 className="mb-16">From your data to a daily plan in nine steps</h2>
        <div className="pipe">{STEPS.map(([Icon, t, d]) => <div className="step" key={t}><Icon size={20} color="var(--primary)" /><h4 className="mt-4">{t}</h4><p className="small muted mt-4">{d}</p></div>)}</div>
      </section>
      <footer className="section center small muted">Educational project · Nutrition guidance is general information, not medical advice.</footer>
    </div>
  );
}
