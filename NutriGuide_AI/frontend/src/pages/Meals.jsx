import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import api, { errText } from "../services/api";
import { useUI } from "../context/UIContext";
import MealCard from "../components/MealCard";
import { TraceBlock } from "../components/ReasoningTrace";
import { Empty, Loading, Modal, VerdictBadge } from "../components/ui";

const SLOTS = ["All", "Breakfast", "Lunch", "Dinner", "Snack"];
const VERDICTS = [["", "All"], ["recommended", "Great match"], ["neutral", "Okay"], ["caution", "Occasionally"], ["avoid", "Avoid"]];

export default function Meals() {
  const { toast } = useUI();
  const [slot, setSlot] = useState("All");
  const [verdict, setVerdict] = useState("");
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      api.get("/meals", { params: { slot: slot === "All" ? undefined : slot, verdict: verdict || undefined, q: q || undefined } })
        .then((r) => setData(r.data)).catch((e) => toast(errText(e), "err"));
    }, 200);
    return () => clearTimeout(t);
  }, [slot, verdict, q, toast]);

  const open = async (m) => {
    setDetail({ meal: m, loading: true });
    try { const { data } = await api.get(`/meals/${m.id}`); setDetail({ meal: { ...m, ...data.meal }, ev: data.evaluation, proof: data.proof }); }
    catch (e) { toast(errText(e), "err"); setDetail(null); }
  };
  const log = async (m) => {
    try { await api.post("/tracker/meal", { slot: m.meal_type?.[0] || "Snack", name: m.name, calories: m.calories, protein: m.protein, carbs: m.carbs, fat: m.fat, fiber: m.fiber || 0, source: "catalogue" }); toast(`${m.name} logged`); }
    catch (e) { toast(errText(e), "err"); }
  };
  const fb = (m, accepted) => api.post("/meals/feedback", { meal_name: m.name, tags: m.tags || [], accepted }).then(() => toast(accepted ? "Learned: you like this" : "Learned: not for you"));

  return (
    <div>
      <div className="page-head"><div><h1>Meals</h1><p>Every meal is judged by the inference engine against your allergies, health rules and goal.</p></div></div>
      <div className="card mb-16">
        <div className="row wrap gap-16">
          <div className="seg">{SLOTS.map((s) => <button key={s} className={slot === s ? "on" : ""} onClick={() => setSlot(s)}>{s}</button>)}</div>
          <div className="seg">{VERDICTS.map(([v, l]) => <button key={v} className={verdict === v ? "on" : ""} onClick={() => setVerdict(v)}>{l}{data && v ? ` ${data.counts[v] ?? 0}` : ""}</button>)}</div>
          <div className="grow" style={{ minWidth: 200, position: "relative" }}>
            <Search size={16} style={{ position: "absolute", left: 12, top: 12, color: "var(--muted)" }} />
            <input className="input" style={{ paddingLeft: 36 }} placeholder="Search meals, ingredients, tags..." value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
      </div>
      {!data ? <Loading /> : data.meals.length === 0 ? <div className="card"><Empty emoji="🔍" title="No meals found"><p className="small">Try a different filter.</p></Empty></div> : (
        <div className="meal-grid">
          {data.meals.map((m) => <MealCard key={m.id} meal={m} onClick={() => open(m)} actions={<button className="btn secondary sm" disabled={m.verdict === "avoid"} onClick={() => log(m)}><Plus size={14} />Log</button>} />)}
        </div>
      )}
      {detail && (
        <Modal title={detail.meal.name} onClose={() => setDetail(null)} wide>
          <div className="row gap-12 wrap"><span style={{ fontSize: 34 }}>{detail.meal.emoji}</span><VerdictBadge verdict={detail.meal.verdict} />
            <span className="muted small">{detail.meal.calories} kcal · P {detail.meal.protein}g · C {detail.meal.carbs}g · F {detail.meal.fat}g · Fibre {detail.meal.fiber}g · Sodium {detail.meal.sodium_mg}mg · GI {detail.meal.glycemic_index}</span></div>
          {detail.loading ? <Loading /> : (
            <>
              <div className="grid g2 mt-16">
                <div><h4 className="mb-8">Ingredients</h4><ul className="small" style={{ paddingLeft: 18, margin: 0 }}>{detail.meal.ingredients?.map((i) => <li key={i}>{i}</li>)}</ul></div>
                <div><h4 className="mb-8">Method</h4><ol className="small" style={{ paddingLeft: 18, margin: 0 }}>{detail.meal.steps?.map((s) => <li key={s}>{s}</li>)}</ol></div>
              </div>
              <div className="row mt-16 wrap">
                <button className="btn secondary sm" onClick={() => fb(detail.meal, true)}>👍 I like this</button>
                <button className="btn secondary sm" onClick={() => fb(detail.meal, false)}>👎 Not for me</button>
              </div>
              <TraceBlock trace={detail.ev} proof={detail.proof} defaultOpen />
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
