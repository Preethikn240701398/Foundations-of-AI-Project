import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Droplets, Flame, Plus, Scale, Trash2, CalendarDays, Check, Sparkles, MessageCircle } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { errText } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import { BmiGauge, Empty, Loading, MacroBar, Ring, Spinner, fmtDate } from "../components/ui";

const greet = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; };

export default function Dashboard() {
  const { refreshProfile } = useAuth();
  const { toast } = useUI();
  const [d, setD] = useState(null);
  const [weight, setWeight] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(() => api.get("/tracker/dashboard").then((r) => setD(r.data)).catch((e) => toast(errText(e), "err")), [toast]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <Loading text="Preparing your dashboard..." />;

  const req = d.requirements, t = d.today.totals;
  const remaining = req.calories - t.calories;
  const water = d.today.water_ml, waterGoal = req.water_ml;

  const run = async (key, fn, msg) => { setBusy(key); try { await fn(); await load(); if (msg) toast(msg); } catch (e) { toast(errText(e), "err"); } finally { setBusy(""); } };
  const logMeal = (m) => run("m" + m.name, () => api.post("/tracker/meal", { slot: m.slot, name: m.name, calories: m.calories, protein: m.protein, carbs: m.carbs, fat: m.fat, fiber: m.fiber || 0, portion: m.portion || 1, source: "plan" }), `${m.name} logged`);
  const addWater = (ml) => run("w", () => api.post("/tracker/water", { ml }));
  const del = (id) => run("d" + id, () => api.delete(`/tracker/entry/${id}`));
  const saveWeight = () => run("wt", async () => { await api.post("/tracker/weight", { weight_kg: Number(weight) }); await refreshProfile(); setWeight(""); }, "Weight saved. Targets updated.");

  const loggedNames = new Set(d.today.entries.map((e) => e.name));
  const plan = d.plan_today;

  return (
    <div>
      <div className="page-head">
        <div><h1>{greet()}, {d.profile.name}</h1><p>Here is how today is going.</p></div>
        <div className="row">
          {d.streak > 0 && <span className="badge good"><Flame size={13} />{d.streak}-day logging streak</span>}
          <Link to="/app/assistant" className="btn secondary"><MessageCircle size={16} />Ask the assistant</Link>
        </div>
      </div>

      <div className="grid g-side">
        <div className="col gap-20">
          <div className="card">
            <div className="card-head"><h3>Today's nutrition</h3><span className="muted small">{req.goal.replace("_", " ")} · {req.calories} kcal target</span></div>
            <div className="row gap-20 wrap" style={{ justifyContent: "center" }}>
              <Ring value={t.calories} max={req.calories} size={190} stroke={16}>
                <b>{Math.abs(remaining)}</b><span className="small muted">{remaining >= 0 ? "kcal left" : "kcal over"}</span>
              </Ring>
              <div className="col grow" style={{ minWidth: 240, gap: 14 }}>
                <MacroBar label="Protein" value={t.protein} target={req.protein_g} color="var(--protein)" />
                <MacroBar label="Carbs" value={t.carbs} target={req.carbs_g} color="var(--carbs)" />
                <MacroBar label="Fat" value={t.fat} target={req.fat_g} color="var(--fat)" />
                <MacroBar label="Fibre" value={t.fiber} target={req.fiber_g} color="var(--fiber)" />
                <div className="small muted">Eaten {t.calories} kcal of {req.calories}</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h3 className="row gap-6"><CalendarDays size={18} />Today's plan{plan && <span className="muted small">· day {plan.day_number} of {plan.total_days}</span>}</h3>
              {plan && <Link to="/app/plan" className="btn ghost sm">Open plan</Link>}
            </div>
            {!plan ? (
              <Empty emoji="📅" title="No active diet plan yet">
                <p className="small">Generate a personalised plan and activate it to see today's meals here.</p>
                <Link to="/app/plan" className="btn mt-12"><Sparkles size={16} />Generate my plan</Link>
              </Empty>
            ) : (
              <div className="col">
                {plan.meals.map((m) => {
                  const done = loggedNames.has(m.name);
                  return (
                    <div key={m.slot} className="row" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                      <div className="meal-emoji" style={{ width: 44, height: 44, fontSize: 24 }}>{m.emoji}</div>
                      <div className="grow"><div className="slot-label">{m.slot}</div><div className="bold">{m.name}</div>
                        <div className="tiny muted">{m.calories} kcal · P {Math.round(m.protein)}g · C {Math.round(m.carbs)}g · F {Math.round(m.fat)}g</div></div>
                      <button className={`btn sm ${done ? "secondary" : ""}`} disabled={done || busy === "m" + m.name} onClick={() => logMeal(m)}>
                        {done ? <><Check size={14} />Logged</> : busy === "m" + m.name ? <Spinner size={14} /> : <><Plus size={14} />Log</>}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-head"><h3>Food diary</h3><span className="muted small">{d.today.entries.length} {d.today.entries.length === 1 ? "entry" : "entries"}</span></div>
            {d.today.entries.length === 0 ? <p className="muted small">Nothing logged yet. Log meals from your plan or the Food scanner.</p> : (
              <table className="tbl"><tbody>
                {d.today.entries.map((e) => (
                  <tr key={e.id}><td><b>{e.name}</b><div className="tiny muted">{e.slot}</div></td><td>{Math.round(e.calories)} kcal</td>
                    <td className="tiny muted">P {Math.round(e.protein)} · C {Math.round(e.carbs)} · F {Math.round(e.fat)}</td>
                    <td style={{ textAlign: "right" }}><button className="btn ghost icon-btn" onClick={() => del(e.id)}><Trash2 size={16} /></button></td></tr>
                ))}
              </tbody></table>
            )}
          </div>
        </div>

        <div className="col gap-20">
          <div className="card">
            <div className="card-head"><h3>Body mass index</h3><span className={`badge ${req.bmi_category === "normal" ? "good" : "caution"}`}>{req.bmi_label}</span></div>
            <BmiGauge bmi={req.bmi} />
            <p className="small muted mt-12">Healthy range for your height: <b>{req.healthy_weight_min}-{req.healthy_weight_max} kg</b>. BMR {req.bmr} kcal · TDEE {req.tdee} kcal.</p>
            {req.warnings.map((w) => <div key={w} className="banner warn mt-12 small">{w}</div>)}
          </div>

          <div className="card">
            <div className="card-head"><h3 className="row gap-6"><Droplets size={18} color="var(--protein)" />Water</h3><span className="small muted">{(water / 1000).toFixed(2)} / {(waterGoal / 1000).toFixed(1)} L</span></div>
            <div className="bar" style={{ height: 12 }}><i style={{ width: `${Math.min(100, (water / waterGoal) * 100)}%`, background: "var(--protein)" }} /></div>
            <div className="row mt-12 wrap">{[250, 500].map((ml) => <button key={ml} className="btn secondary sm" onClick={() => addWater(ml)} disabled={busy === "w"}><Plus size={14} />{ml} ml</button>)}</div>
          </div>

          <div className="card">
            <div className="card-head"><h3 className="row gap-6"><Scale size={18} />Weight</h3><span className="small muted">{d.profile.weight} kg now</span></div>
            {d.weights.length > 1 && (
              <div style={{ height: 110, marginBottom: 8 }}>
                <ResponsiveContainer><AreaChart data={d.weights}>
                  <defs><linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--primary)" stopOpacity={0.35} /><stop offset="100%" stopColor="var(--primary)" stopOpacity={0} /></linearGradient></defs>
                  <XAxis dataKey="date" hide /><YAxis hide domain={["dataMin - 1", "dataMax + 1"]} />
                  <Tooltip formatter={(v) => [`${v} kg`, "Weight"]} labelFormatter={fmtDate} />
                  <Area dataKey="weight_kg" stroke="var(--primary)" strokeWidth={2.5} fill="url(#wg)" />
                </AreaChart></ResponsiveContainer>
              </div>
            )}
            <div className="row">
              <input className="input" type="number" step="0.1" placeholder="Log today's weight (kg)" value={weight} onChange={(e) => setWeight(e.target.value)} />
              <button className="btn" onClick={saveWeight} disabled={!weight || busy === "wt"}>Save</button>
            </div>
            <p className="tiny muted mt-8">Saving a weigh-in recalculates BMI and your calorie target.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
