import { useEffect, useState } from "react";
import { Flame, Timer, BedDouble } from "lucide-react";
import api, { errText } from "../services/api";
import { useUI } from "../context/UIContext";
import { Field, Loading, Seg, Spinner, titleCase } from "../components/ui";

const EMOJI = { full_body: "🏋️", upper: "💪", lower: "🦵", push: "🤜", pull: "🧗", cardio: "🏃", rest: "🛌" };

export default function Workouts() {
  const { toast } = useUI();
  const [minutes, setMinutes] = useState(45);
  const [split, setSplit] = useState("");
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(0);
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    try { const { data } = await api.post("/workout-planner/generate", { minutes, split_type: split || null }); setData(data); }
    catch (e) { toast(errText(e), "err"); } finally { setBusy(false); }
  };
  useEffect(() => { generate(); }, []); // eslint-disable-line

  return (
    <div>
      <div className="page-head"><div><h1>Workouts</h1><p>A weekly schedule matched to your activity level and goal, with recovery days built in.</p></div></div>
      <div className="card mb-16">
        <div className="row wrap gap-20" style={{ alignItems: "flex-end" }}>
          <Field label="Split"><Seg value={split} onChange={setSplit} options={[["", "Auto"], ["full_body", "Full body"], ["upper_lower", "Upper / lower"], ["push_pull", "Push / pull / legs"]]} /></Field>
          <Field label={`Session length: ${minutes} min`}><input type="range" min="20" max="90" step="5" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} style={{ accentColor: "var(--primary)" }} /></Field>
          <div className="grow" />
          <button className="btn" onClick={generate} disabled={busy}>{busy ? <Spinner /> : "Build schedule"}</button>
        </div>
      </div>
      {!data ? <Loading /> : (
        <>
          <div className="grid g3 mb-16">
            <div className="card"><div className="stat"><span className="v">{data.summary.sessions}</span><span className="l">training sessions / week</span></div></div>
            <div className="card"><div className="stat"><span className="v">{data.summary.weekly_burn}</span><span className="l">estimated kcal burned / week</span></div></div>
            <div className="card"><div className="stat"><span className="v">{titleCase(data.split)}</span><span className="l">split · protein goal {data.summary.protein_target} g</span></div></div>
          </div>
          <div className="grid g-side">
            <div className="col">
              {data.week.map((w, i) => (
                <button key={w.day} onClick={() => setOpen(i)} className="card row" style={{ textAlign: "left", cursor: "pointer", borderColor: open === i ? "var(--primary)" : undefined, opacity: w.type === "rest" ? 0.8 : 1 }}>
                  <div className="meal-emoji">{EMOJI[w.type] || "🏋️"}</div>
                  <div className="grow"><div className="slot-label">{w.day}</div><div className="bold">{w.title}</div>
                    <div className="tiny muted row gap-12"><span className="row gap-4"><Timer size={12} />{w.minutes} min</span><span className="row gap-4"><Flame size={12} />{w.calories} kcal</span></div></div>
                </button>
              ))}
            </div>
            <div className="card" style={{ alignSelf: "start" }}>
              {(() => { const w = data.week[open]; return (<>
                <div className="card-head"><h3>{w.day} · {w.title}</h3>{w.type === "rest" && <BedDouble size={20} color="var(--muted)" />}</div>
                <table className="tbl"><thead><tr><th>Exercise</th><th>Sets</th><th>Reps</th></tr></thead>
                  <tbody>{w.exercises.map((e) => <tr key={e.name}><td className="bold">{e.name}</td><td>{e.sets}</td><td>{e.reps}</td></tr>)}</tbody></table>
                <p className="small muted mt-12">Eat a meal with carbohydrate and protein within two hours of training, and drink water through the session.</p>
              </>); })()}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
