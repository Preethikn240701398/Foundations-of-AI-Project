import { useState } from "react";
import { Plus, ScanLine, Search } from "lucide-react";
import api, { errText } from "../services/api";
import { useUI } from "../context/UIContext";
import { MacroPills, Spinner, VerdictBadge } from "../components/ui";

const EXAMPLES = ["Idli", "Chicken biryani", "Dal", "Samosa", "Salmon", "Oats", "Paneer", "Banana"];

export default function FoodScanner() {
  const { toast } = useUI();
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [pick, setPick] = useState(null);
  const [portion, setPortion] = useState(1);
  const [busy, setBusy] = useState(false);

  const scan = async (text = q) => {
    if (!text.trim()) return;
    setQ(text); setBusy(true);
    try { const { data } = await api.post("/food-scanner/identify", { query: text }); setRes(data); setPick(data.candidates[0] || null); setPortion(1); }
    catch (e) { toast(errText(e), "err"); } finally { setBusy(false); }
  };
  const add = async () => {
    const c = pick; const k = (v) => Math.round((v || 0) * portion * 10) / 10;
    try { await api.post("/tracker/meal", { slot: "Snack", name: c.name, calories: Math.round((c.calories || 0) * portion), protein: k(c.protein), carbs: k(c.carbs), fat: k(c.fat), fiber: k(c.fiber), portion, source: "scanner" }); toast(`${c.name} added to your diary`); }
    catch (e) { toast(errText(e), "err"); }
  };

  return (
    <div>
      <div className="page-head"><div><h1>Food scanner</h1><p>Type or pick a food. The scanner ranks what it might be, then checks it against your profile.</p></div></div>
      <div className="card mb-16">
        <form className="row" onSubmit={(e) => { e.preventDefault(); scan(); }}>
          <div className="grow" style={{ position: "relative" }}><Search size={16} style={{ position: "absolute", left: 12, top: 12, color: "var(--muted)" }} />
            <input className="input" style={{ paddingLeft: 36 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. chicken biryani" /></div>
          <button className="btn" disabled={busy}>{busy ? <Spinner /> : <><ScanLine size={17} />Identify</>}</button>
        </form>
        <div className="chips mt-12">{EXAMPLES.map((x) => <button key={x} className="chip" onClick={() => scan(x)}>{x}</button>)}</div>
      </div>

      {res && res.candidates.length === 0 && <div className="card"><p className="muted">Nothing matched. Try a simpler name.</p></div>}
      {res && res.candidates.length > 0 && (
        <div className="grid g-side">
          <div className="card">
            <div className="card-head"><h3>Possible matches</h3>{res.needs_confirmation && <span className="badge caution">Low confidence: please confirm</span>}</div>
            <div className="col">
              {res.candidates.map((c) => (
                <button key={c.name} className="card flat row" style={{ textAlign: "left", cursor: "pointer", borderColor: pick?.name === c.name ? "var(--primary)" : undefined }} onClick={() => setPick(c)}>
                  <div className="grow"><div className="bold">{c.emoji || ""} {c.name}</div>
                    <div className="bar mt-4" style={{ height: 6 }}><i style={{ width: `${Math.round(c.confidence * 100)}%`, background: "var(--primary)" }} /></div></div>
                  <div className="tiny muted" style={{ width: 54, textAlign: "right" }}>{Math.round(c.confidence * 100)}%</div>
                  <VerdictBadge verdict={c.verdict} />
                </button>
              ))}
            </div>
            <p className="tiny muted mt-12">The scanner keeps a ranked belief state and asks for confirmation when its best guess is weak (search in a partially observable environment).</p>
          </div>
          {pick && (
            <div className="card" style={{ alignSelf: "start" }}>
              <div className="row between"><h3>{pick.emoji} {pick.name}</h3><VerdictBadge verdict={pick.verdict} /></div>
              <div className="stat mt-12"><span className="v">{Math.round((pick.calories || 0) * portion)} <span className="muted small" style={{ fontWeight: 500 }}>kcal</span></span></div>
              <div className="mt-8"><MacroPills m={{ protein: (pick.protein || 0) * portion, carbs: (pick.carbs || 0) * portion, fat: (pick.fat || 0) * portion }} /></div>
              <div className="mt-12 small muted">Glycaemic index {pick.glycemic_index ?? "n/a"}</div>
              {pick.why?.length > 0 && <div className="col mt-12 gap-4">{pick.why.map((w) => <div key={w} className="small">• {w}</div>)}</div>}
              <div className="divider" />
              <div className="row"><span className="small bold">Serving</span>
                <div className="seg">{[0.5, 1, 1.5, 2].map((p) => <button key={p} className={portion === p ? "on" : ""} onClick={() => setPortion(p)}>{p}x</button>)}</div></div>
              <button className="btn block mt-12" onClick={add} disabled={pick.verdict === "avoid"}><Plus size={16} />{pick.verdict === "avoid" ? "Not recommended for you" : "Add to diary"}</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
