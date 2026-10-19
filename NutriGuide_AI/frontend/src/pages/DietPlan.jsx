import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Check, Download, Info, Plus, Printer, Repeat, Save, Sparkles, Trash2, Zap, FolderOpen, Cpu } from "lucide-react";
import api, { errText } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import MealCard from "../components/MealCard";
import { TraceBlock } from "../components/ReasoningTrace";
import { Empty, Field, Loading, MacroBar, Modal, Seg, Spinner, VerdictBadge, fmtDate, titleCase } from "../components/ui";

const STRATEGIES = [["csp", "CSP solver"], ["astar", "A* search"], ["bfs", "BFS"]];
const STRATEGY_INFO = {
  csp: "Constraint satisfaction with backtracking, MRV ordering and forward checking. Guarantees every rule and nutrition constraint.",
  astar: "Informed search: f(n) = g(n) + h(n). Finds the plan with the lowest calorie-fit and ranking cost.",
  bfs: "Uninformed breadth-first search. Explores combinations level by level until one fits your calories.",
};

const sum = (arr, k) => arr.reduce((s, m) => s + (Number(m[k]) || 0), 0);
function recompute(day, target) {
  const m = day.meals;
  const totals = { calories: Math.round(sum(m, "calories")), protein: +sum(m, "protein").toFixed(1), carbs: +sum(m, "carbs").toFixed(1),
    fat: +sum(m, "fat").toFixed(1), fiber: +sum(m, "fiber").toFixed(1), sodium_mg: Math.round(sum(m, "sodium_mg")),
    gi_avg: Math.round(sum(m, "glycemic_index") / (m.length || 1)) };
  return { ...day, totals, accuracy: +(100 - (Math.abs(totals.calories - target) / target) * 100).toFixed(1) };
}
function summarize(plan) {
  const d = plan.days, n = d.length || 1;
  const avg = (k) => +(d.reduce((s, x) => s + x.totals[k], 0) / n).toFixed(1);
  return { ...plan.summary, avg_calories: avg("calories"), avg_protein: avg("protein"), avg_carbs: avg("carbs"), avg_fat: avg("fat"), avg_fiber: avg("fiber"),
    avg_accuracy: +(d.reduce((s, x) => s + x.accuracy, 0) / n).toFixed(1), unique_meals: new Set(d.flatMap((x) => x.meals.map((m) => m.name))).size };
}

export default function DietPlan() {
  const { profile } = useAuth();
  const { toast } = useUI();
  const [params] = useSearchParams();
  const [opts, setOpts] = useState({ days: 7, strategy: "csp", optimize: true });
  const [plan, setPlan] = useState(null);
  const [savedId, setSavedId] = useState(null);
  const [name, setName] = useState("My diet plan");
  const [dirty, setDirty] = useState(false);
  const [day, setDay] = useState(0);
  const [tab, setTab] = useState("menu");
  const [busy, setBusy] = useState("");
  const [saved, setSaved] = useState(null);
  const [swap, setSwap] = useState(null);
  const [detail, setDetail] = useState(null);
  const [checked, setChecked] = useState({});

  const loadSaved = useCallback(() => api.get("/diet-plans").then((r) => setSaved(r.data)), []);
  useEffect(() => { loadSaved(); }, [loadSaved]);

  const generate = async () => {
    setBusy("gen");
    try {
      const { data } = await api.post("/diet-plans/generate", opts);
      setPlan(data); setSavedId(null); setDay(0); setDirty(true); setTab("menu"); setChecked({});
      toast(`Plan ready · ${data.summary.avg_accuracy}% calorie accuracy`);
    } catch (e) { toast(errText(e), "err"); } finally { setBusy(""); }
  };

  const save = async (activate = true) => {
    setBusy("save");
    try {
      if (savedId) { await api.put(`/diet-plans/${savedId}`, { name, plan }); if (activate) await api.post(`/diet-plans/${savedId}/activate`); }
      else { const { data } = await api.post("/diet-plans", { name, plan, activate }); setSavedId(data.id); }
      setDirty(false); await loadSaved();
      toast(activate ? "Plan saved and set as your active plan" : "Plan saved");
    } catch (e) { toast(errText(e), "err"); } finally { setBusy(""); }
  };

  const open = async (id) => {
    setBusy("open" + id);
    try {
      const { data } = await api.get(`/diet-plans/${id}`);
      setPlan(data.plan); setSavedId(id); setName(data.name); setDay(0); setDirty(false); setTab("menu"); window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) { toast(errText(e), "err"); } finally { setBusy(""); }
  };
  const activate = async (id) => { await api.post(`/diet-plans/${id}/activate`); await loadSaved(); toast("Active plan changed"); };
  const remove = async (id) => { await api.delete(`/diet-plans/${id}`); if (id === savedId) { setSavedId(null); } await loadSaved(); toast("Plan deleted"); };

  const openSwap = async (mealIdx) => {
    const d = plan.days[day]; const slot = d.meals[mealIdx].slot;
    setSwap({ idx: mealIdx, slot, loading: true, options: [] });
    try {
      const { data } = await api.post("/diet-plans/alternatives", { slot, exclude: d.meals.map((m) => m.name), target_kcal: plan.targets.calories });
      setSwap({ idx: mealIdx, slot, loading: false, options: data.alternatives });
    } catch (e) { toast(errText(e), "err"); setSwap(null); }
  };
  const applySwap = (opt) => {
    const days = plan.days.map((d, i) => {
      if (i !== day) return d;
      const meals = d.meals.map((m, j) => (j === swap.idx ? { slot: m.slot, ...opt } : m));
      return recompute({ ...d, meals }, plan.targets.calories);
    });
    const np = { ...plan, days }; np.summary = summarize(np);
    setPlan(np); setDirty(true); setSwap(null); toast("Meal swapped");
  };

  const logMeal = async (m) => {
    try { await api.post("/tracker/meal", { slot: m.slot, name: m.name, calories: m.calories, protein: m.protein, carbs: m.carbs, fat: m.fat, fiber: m.fiber || 0, portion: m.portion || 1, source: "plan" }); toast(`${m.name} added to today's diary`); }
    catch (e) { toast(errText(e), "err"); }
  };
  const feedback = (m, accepted) => api.post("/meals/feedback", { meal_name: m.name, tags: m.tags || [], accepted }).then(() => toast(accepted ? "Noted. You'll see more like this." : "Noted. You'll see less like this."));

  const openDetail = async (m) => {
    setDetail({ meal: m, loading: true });
    try { const { data } = m.id ? await api.get(`/meals/${m.id}`) : { data: null }; setDetail({ meal: m, ev: data?.evaluation, proof: data?.proof }); }
    catch { setDetail({ meal: m }); }
  };

  const shopping = useMemo(() => {
    if (!plan) return [];
    const map = {};
    plan.days.forEach((d) => d.meals.forEach((m) => (m.ingredients || []).forEach((i) => { map[i] = (map[i] || 0) + 1; })));
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
  }, [plan]);
  const downloadList = () => {
    const txt = `NutriGuide AI shopping list (${plan.days.length} days)\n\n` + shopping.map(([i, n]) => `[ ] ${i}${n > 1 ? `  (used in ${n} meals)` : ""}`).join("\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([txt], { type: "text/plain" })); a.download = "shopping-list.txt"; a.click();
  };

  const d = plan?.days[day];
  const chart = plan?.days.map((x) => ({ name: x.weekday, calories: x.totals.calories, target: plan.targets.calories }));
  const constraints = [
    ...(profile?.allergies || []).map((a) => `No ${a}`), ...(profile?.dietary_restrictions || []).map((a) => titleCase(a)),
    ...(Array.isArray(profile?.health_condition) ? profile.health_condition : []).map(titleCase),
  ];

  return (
    <div>
      <div className="page-head">
        <div><h1>Diet plan</h1><p>A balanced menu built from your needs, rules and preferences.</p></div>
      </div>

      {params.get("welcome") && !plan && <div className="banner good mb-16"><Sparkles size={18} style={{ flex: "none" }} /><span>Your profile is ready. Press <b>Generate plan</b> to build your first menu.</span></div>}

      <div className="card mb-16">
        <div className="row wrap gap-20" style={{ alignItems: "flex-end" }}>
          <Field label="Length"><Seg value={String(opts.days)} onChange={(v) => setOpts({ ...opts, days: Number(v) })} options={[["3", "3 days"], ["7", "7 days"], ["14", "14 days"]]} /></Field>
          <Field label="Algorithm"><Seg value={opts.strategy} onChange={(strategy) => setOpts({ ...opts, strategy })} options={STRATEGIES} /></Field>
          <Field label="Week optimiser"><label className="row" style={{ cursor: "pointer", height: 40 }}><input type="checkbox" checked={opts.optimize} onChange={(e) => setOpts({ ...opts, optimize: e.target.checked })} />Simulated annealing</label></Field>
          <div className="grow" />
          <button className="btn lg" onClick={generate} disabled={busy === "gen"}>{busy === "gen" ? <><Spinner />Solving...</> : <><Zap size={18} />Generate plan</>}</button>
        </div>
        <p className="small muted mt-12"><Cpu size={13} style={{ verticalAlign: "-2px" }} /> {STRATEGY_INFO[opts.strategy]}</p>
        {constraints.length > 0 && <div className="row wrap mt-8 gap-6"><span className="tiny muted">Rules applied:</span>{constraints.map((c) => <span key={c} className="tag">{c}</span>)}</div>}
      </div>

      {!plan && !busy && (
        <div className="card"><Empty emoji="🧠" title="Ready when you are"><p className="small">The solver removes unsafe meals, ranks the rest, then picks one meal per slot per day.</p></Empty></div>
      )}
      {busy === "gen" && !plan && <Loading text="Running the inference engine and solver..." />}

      {plan && d && (
        <div className="fade-in">
          <div className="grid g4 mb-16">
            <div className="card"><div className="stat"><span className="v">{Math.round(plan.summary.avg_calories)}</span><span className="l">avg kcal / day (target {plan.targets.calories})</span></div></div>
            <div className="card"><div className="stat"><span className="v">{plan.summary.avg_accuracy}%</span><span className="l">calorie accuracy</span></div></div>
            <div className="card"><div className="stat"><span className="v">{Math.round(plan.summary.avg_protein)}g</span><span className="l">avg protein (target {plan.targets.protein}g)</span></div></div>
            <div className="card"><div className="stat"><span className="v">{plan.summary.unique_meals}</span><span className="l">different meals</span></div></div>
          </div>

          <div className="card mb-16">
            <div className="row wrap gap-12" style={{ alignItems: "flex-end" }}>
              <div className="grow" style={{ minWidth: 220 }}><Field label="Plan name"><input className="input" value={name} onChange={(e) => { setName(e.target.value); setDirty(true); }} /></Field></div>
              <button className="btn" onClick={() => save(true)} disabled={busy === "save" || (!dirty && !!savedId)}>{busy === "save" ? <Spinner /> : <><Save size={16} />{savedId ? "Update & activate" : "Save & activate"}</>}</button>
              <button className="btn secondary no-print" onClick={() => window.print()}><Printer size={16} />Print</button>
            </div>
            {savedId && !dirty && <p className="small mt-8" style={{ color: "var(--primary)" }}><Check size={14} style={{ verticalAlign: "-2px" }} /> Saved to your account</p>}
          </div>

          <div className="tabs no-print">
            {[["menu", "Daily menu"], ["overview", "Week overview"], ["shopping", `Shopping list (${shopping.length})`], ["algorithm", "How it was solved"]].map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
          </div>

          {tab === "menu" && (
            <>
              <div className="day-tabs">
                {plan.days.map((x, i) => <button key={i} className={`day-tab ${i === day ? "on" : ""}`} onClick={() => setDay(i)}><small>{x.weekday}</small><b>{fmtDate(x.date)}</b></button>)}
              </div>
              <div className="grid g-side">
                <div className="col" style={{ alignContent: "start" }}>
                  {d.meals.map((m, i) => (
                    <MealCard key={m.slot + m.name} meal={m} showSlot={m.slot} onClick={() => openDetail(m)} actions={<>
                      <button className="btn secondary sm" onClick={() => openSwap(i)}><Repeat size={14} />Swap</button>
                      <button className="btn secondary sm" onClick={() => logMeal(m)}><Plus size={14} />Log</button>
                    </>} />
                  ))}
                </div>
                <div className="card" style={{ alignSelf: "start" }}>
                  <div className="card-head"><h3>Day totals</h3><span className="badge good">{d.accuracy}% match</span></div>
                  <div className="stat mb-16"><span className="v">{d.totals.calories} <span className="muted small" style={{ fontWeight: 500 }}>/ {plan.targets.calories} kcal</span></span></div>
                  <div className="col" style={{ gap: 12 }}>
                    <MacroBar label="Protein" value={d.totals.protein} target={plan.targets.protein} color="var(--protein)" />
                    <MacroBar label="Carbs" value={d.totals.carbs} target={plan.targets.carbs} color="var(--carbs)" />
                    <MacroBar label="Fat" value={d.totals.fat} target={plan.targets.fat} color="var(--fat)" />
                    <MacroBar label="Fibre" value={d.totals.fiber} target={plan.targets.fiber} color="var(--fiber)" />
                    <MacroBar label="Sodium" value={d.totals.sodium_mg} target={plan.targets.sodium_limit} unit="mg" color="var(--muted)" />
                  </div>
                  <p className="small muted mt-12">Average glycaemic index {d.totals.gi_avg} (limit {plan.targets.glycemic_max}).</p>
                </div>
              </div>
            </>
          )}

          {tab === "overview" && (
            <div className="card">
              <h3 className="mb-16">Calories per day vs target</h3>
              <div style={{ height: 280 }}>
                <ResponsiveContainer><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" stroke="var(--muted)" tickLine={false} /><YAxis stroke="var(--muted)" tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)" }} />
                  <ReferenceLine y={plan.targets.calories} stroke="var(--fat)" strokeDasharray="5 4" label={{ value: "target", fill: "var(--fat)", fontSize: 12, position: "right" }} />
                  <Bar dataKey="calories" fill="var(--primary)" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
              </div>
              <div className="grid g3 mt-16">
                {plan.days.map((x, i) => <button key={i} className="card soft" style={{ textAlign: "left", cursor: "pointer", border: 0 }} onClick={() => { setDay(i); setTab("menu"); }}>
                  <div className="row between"><b>{x.weekday} {fmtDate(x.date)}</b><span className="tiny muted">{x.totals.calories} kcal</span></div>
                  <div className="tiny muted mt-4">{x.meals.map((m) => m.emoji).join(" ")} · {x.meals.map((m) => m.name.split(" ")[0]).join(", ")}</div></button>)}
              </div>
            </div>
          )}

          {tab === "shopping" && (
            <div className="card">
              <div className="card-head"><h3>Shopping list</h3><div className="row no-print"><button className="btn secondary sm" onClick={downloadList}><Download size={14} />Download</button><button className="btn secondary sm" onClick={() => window.print()}><Printer size={14} />Print</button></div></div>
              <div className="grid g3" style={{ gap: 6 }}>
                {shopping.map(([item, n]) => (
                  <label key={item} className="row" style={{ cursor: "pointer", padding: "6px 8px", borderRadius: 10, background: checked[item] ? "var(--primary-soft)" : "transparent" }}>
                    <input type="checkbox" checked={!!checked[item]} onChange={(e) => setChecked({ ...checked, [item]: e.target.checked })} />
                    <span style={{ textDecoration: checked[item] ? "line-through" : "none" }}>{item}</span>{n > 1 && <span className="tiny muted">×{n}</span>}
                  </label>
                ))}
              </div>
            </div>
          )}

          {tab === "algorithm" && (
            <div className="col gap-16">
              <div className="algo-strip">
                <span>Strategy <b>{plan.algorithm.strategy.toUpperCase()}</b></span>
                <span>Nodes explored <b>{plan.algorithm.nodes}</b></span>
                {plan.algorithm.backtracks > 0 && <span>Backtracks <b>{plan.algorithm.backtracks}</b></span>}
                {plan.algorithm.pruned > 0 && <span>Branches pruned <b>{plan.algorithm.pruned}</b></span>}
                {plan.algorithm.annealing && <span>Annealing cost <b>{plan.algorithm.annealing.cost_before} → {plan.algorithm.annealing.cost_after}</b> ({plan.algorithm.annealing.accepted} moves accepted)</span>}
              </div>
              <div className="grid g2">
                <div className="card"><h3 className="mb-8">Pipeline used for this plan</h3>
                  <ol className="small col" style={{ paddingLeft: 18, margin: 0, gap: 8 }}>
                    <li>The <b>inference engine</b> judged every meal against your facts (forward chaining).</li>
                    <li>Meals marked <b>avoid</b> were removed. The rest were ranked by rule score, learned preference and calorie fit.</li>
                    <li>Each meal got a <b>portion</b> (0.75x–2x) to fit its slot's calorie share.</li>
                    <li>The <b>{plan.algorithm.strategy.toUpperCase()}</b> search chose one meal per slot, avoiding repeats.</li>
                    {plan.algorithm.annealing && <li><b>Simulated annealing</b> swapped single meals across the week to reduce total error.</li>}
                    <li>Portions were calibrated so each day lands on your calorie target.</li>
                  </ol></div>
                <div className="card"><h3 className="mb-8">Candidates per slot</h3>
                  <table className="tbl"><tbody>{Object.entries(plan.algorithm.candidates_per_slot).map(([s, n]) => <tr key={s}><td>{s}</td><td><b>{n}</b> safe, ranked candidates</td></tr>)}</tbody></table>
                  {plan.algorithm.relaxation.some((r) => r !== "n/a") && <p className="small muted mt-12">Constraint strictness per day: {plan.algorithm.relaxation.join(", ")}</p>}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-24">
        <h2 className="mb-16 row gap-8"><FolderOpen size={20} />Saved plans</h2>
        {saved === null ? <Loading /> : saved.length === 0 ? <div className="card"><p className="muted small">Plans you save will appear here.</p></div> : (
          <div className="grid g3">
            {saved.map((p) => (
              <div key={p.id} className="card col" style={{ gap: 8 }}>
                <div className="row between"><h3 style={{ fontSize: 16 }}>{p.name}</h3>{p.is_active && <span className="badge good">Active</span>}</div>
                <div className="small muted">{p.days} days · {p.strategy?.toUpperCase()} · {fmtDate(p.created_at)}</div>
                <div className="small">Avg {p.avg_calories} kcal · {p.avg_accuracy}% accuracy</div>
                <div className="row wrap">
                  <button className="btn secondary sm" onClick={() => open(p.id)} disabled={busy === "open" + p.id}>Open</button>
                  {!p.is_active && <button className="btn secondary sm" onClick={() => activate(p.id)}>Activate</button>}
                  <button className="btn ghost sm" onClick={() => remove(p.id)}><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {swap && (
        <Modal title={`Swap ${swap.slot.toLowerCase()}`} onClose={() => setSwap(null)} wide>
          {swap.loading ? <Loading text="Finding safe alternatives..." /> : swap.options.length === 0 ? <p className="muted">No alternatives available.</p> : (
            <div className="grid g2">{swap.options.map((o) => <MealCard key={o.name} meal={o} onClick={() => applySwap(o)} actions={<button className="btn sm" onClick={() => applySwap(o)}>Use this meal</button>} />)}</div>
          )}
        </Modal>
      )}

      {detail && (
        <Modal title={detail.meal.name} onClose={() => setDetail(null)} wide>
          <div className="row gap-12 wrap"><span style={{ fontSize: 34 }}>{detail.meal.emoji}</span><VerdictBadge verdict={detail.meal.verdict} />
            <span className="muted small">{detail.meal.calories} kcal · {detail.meal.portion}x serving · P {Math.round(detail.meal.protein)}g · C {Math.round(detail.meal.carbs)}g · F {Math.round(detail.meal.fat)}g</span></div>
          <div className="grid g2 mt-16">
            <div><h4 className="mb-8">Ingredients</h4><ul className="small" style={{ paddingLeft: 18, margin: 0 }}>{detail.meal.ingredients?.map((i) => <li key={i}>{i}</li>)}</ul></div>
            <div><h4 className="mb-8">Method</h4><ol className="small" style={{ paddingLeft: 18, margin: 0 }}>{detail.meal.steps?.map((s) => <li key={s}>{s}</li>)}</ol></div>
          </div>
          <div className="row mt-16"><button className="btn secondary sm" onClick={() => feedback(detail.meal, true)}>👍 I like this</button><button className="btn secondary sm" onClick={() => feedback(detail.meal, false)}>👎 Not for me</button></div>
          {detail.ev && <TraceBlock trace={detail.ev} proof={detail.proof} />}
        </Modal>
      )}
    </div>
  );
}
