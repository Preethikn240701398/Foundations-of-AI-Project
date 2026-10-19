import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Play, Search } from "lucide-react";
import api, { errText } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import { Chips, Field, Loading, Seg, Spinner, VerdictBadge, titleCase } from "../components/ui";
import { Facts, FiredRules, Proof } from "../components/ReasoningTrace";

const TYPE_BADGE = { derive: "neutral", reject: "avoid", caution: "caution", prefer: "good" };

function RuleCard({ r }) {
  return (
    <div className="card flat">
      <div className="row between"><div className="row"><span className={`badge ${TYPE_BADGE[r.type]}`}>{r.id}</span><b className="small">{r.text.replace("{a}", "X")}</b></div>
        <span className="tiny muted">{r.type}{r.weight ? ` · ${r.weight}` : ""}</span></div>
      <div className="rule-text mt-8"><span className="kw">IF</span> {r.if.replace(/ AND /g, " AND ").split(" AND ").map((c, i) => <span key={i}>{i > 0 && <span className="kw"> AND </span>}{c}</span>)} <span className="kw">THEN</span> {r.then}</div>
    </div>
  );
}

function Playground({ items }) {
  const { profile } = useAuth();
  const { toast } = useUI();
  const [item, setItem] = useState("Chicken biryani");
  const [ov, setOv] = useState({ allergies: null, health_condition: null, dietary_restrictions: null, goal: null });
  const [opts, setOpts] = useState(null);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/nutrition/options").then((r) => setOpts(r.data)); }, []);
  const cur = (k) => ov[k] ?? (k === "goal" ? profile.goal : Array.isArray(profile[k]) ? profile[k] : []);
  const setO = (k) => (v) => setOv({ ...ov, [k]: v });

  const run = async () => {
    setBusy(true);
    const overrides = Object.fromEntries(Object.entries(ov).filter(([, v]) => v !== null));
    try { const { data } = await api.post("/knowledge/infer", { item_name: item, overrides }); setRes(data); } catch (e) { toast(errText(e), "err"); } finally { setBusy(false); }
  };
  useEffect(() => { run(); }, []); // eslint-disable-line

  return (
    <div className="grid g-side">
      <div className="card">
        <h3 className="mb-8">What-if playground</h3>
        <p className="small muted mb-16">Pick a food and change the profile to watch the verdict change. The engine re-runs with your what-if facts. Nothing is saved.</p>
        <div className="col gap-16">
          <Field label="Food or meal"><input className="input" list="kb-items" value={item} onChange={(e) => setItem(e.target.value)} /><datalist id="kb-items">{items.map((i) => <option key={i} value={i} />)}</datalist></Field>
          {opts && <>
            <Field label="Health conditions"><Chips options={opts.conditions.map((c) => c.id)} labels={Object.fromEntries(opts.conditions.map((c) => [c.id, c.label]))} value={cur("health_condition")} onChange={setO("health_condition")} /></Field>
            <Field label="Allergies"><Chips options={opts.allergens} value={cur("allergies")} onChange={setO("allergies")} labels={Object.fromEntries(opts.allergens.map((a) => [a, titleCase(a)]))} /></Field>
            <Field label="Eating style"><Chips options={opts.diets.map((d) => d.id)} labels={Object.fromEntries(opts.diets.map((d) => [d.id, titleCase(d.id)]))} value={cur("dietary_restrictions")} onChange={setO("dietary_restrictions")} /></Field>
            <Field label="Goal"><Seg value={cur("goal")} onChange={setO("goal")} options={[["weight_loss", "Lose"], ["balanced", "Balanced"], ["muscle_gain", "Muscle"], ["weight_gain", "Gain"]]} /></Field>
          </>}
          <div className="row"><button className="btn" onClick={run} disabled={busy}>{busy ? <Spinner /> : <><Play size={15} />Run inference</>}</button>
            <button className="btn ghost" onClick={() => { setOv({ allergies: null, health_condition: null, dietary_restrictions: null, goal: null }); }}>Reset to my profile</button></div>
        </div>
      </div>
      <div className="col gap-16">
        {res && <>
          <div className="card">
            <div className="row between"><h3>{res.item.emoji} {res.item.name}</h3><VerdictBadge verdict={res.evaluation.verdict} /></div>
            <div className="small muted mt-4">score {res.evaluation.score}</div>
            <h4 className="mt-16 mb-8">Facts about you</h4><Facts facts={res.user_facts} derived={res.evaluation.derived} />
            <h4 className="mt-12 mb-8">Facts about the food</h4><Facts facts={res.item_facts} />
          </div>
          <div className="card"><h4 className="mb-8">Forward chaining trace</h4><FiredRules fired={res.evaluation.fired} /></div>
          {res.proof && <div className="card"><h4 className="mb-8">Backward chaining proof</h4><Proof node={res.proof} /></div>}
        </>}
      </div>
    </div>
  );
}

export default function KnowledgeBase() {
  const { toast } = useUI();
  const [tab, setTab] = useState("overview");
  const [ov, setOv] = useState(null);
  const [rules, setRules] = useState(null);
  const [foods, setFoods] = useState(null);
  const [meals, setMeals] = useState([]);
  const [cat, setCat] = useState("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/knowledge/overview").then((r) => setOv(r.data)).catch((e) => toast(errText(e), "err"));
    api.get("/knowledge/rules").then((r) => setRules(r.data));
    api.get("/knowledge/foods").then((r) => setFoods(r.data));
    api.get("/meals").then((r) => setMeals(r.data.meals));
  }, [toast]);

  const shown = useMemo(() => (rules?.rules || []).filter((r) => (cat === "all" || r.cat === cat) && (!q || (r.text + r.if + r.id).toLowerCase().includes(q.toLowerCase()))), [rules, cat, q]);
  if (!ov) return <Loading />;

  return (
    <div>
      <div className="page-head"><div><h1>Knowledge base</h1><p>The facts and rules behind every recommendation. Rules are plain data you can read and extend.</p></div></div>
      <div className="tabs">{[["overview", "Overview"], ["rules", `Rules (${ov.rule_count})`], ["ontology", "Ontology"], ["foods", "Foods"], ["play", "Inference playground"]].map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === "overview" && (
        <div className="col gap-20">
          <div className="grid g4">
            {[[ov.rule_count, "IF-THEN rules"], [ov.meal_count, "meals"], [ov.food_count, "foods"], [ov.conditions.length, "health conditions"]].map(([v, l]) => <div key={l} className="card"><div className="stat"><span className="v">{v}</span><span className="l">{l}</span></div></div>)}
          </div>
          <div className="card">
            <h3 className="mb-16">How a decision is made</h3>
            <div className="row wrap gap-12" style={{ alignItems: "stretch" }}>
              {[["1. Facts", "Your profile and the food's nutrition become symbols like condition(diabetes) and item(high_gi)."], ["2. Rules", "IF-THEN rules link facts to needs and verdicts."], ["3. Forward chaining", "The engine fires rules repeatedly, deriving new facts such as need(low_gi)."], ["4. Verdict", "Reject, caution or prefer rules give a score and a verdict."], ["5. Backward chaining", "Starting from the verdict, the engine proves it back to the facts."]].map(([t, d], i, a) => (
                <div key={t} className="row" style={{ flex: "1 1 170px" }}><div className="card soft grow" style={{ height: "100%" }}><b>{t}</b><p className="small muted mt-4">{d}</p></div>{i < a.length - 1 && <ArrowRight size={18} color="var(--muted)" />}</div>))}
            </div>
          </div>
          <div className="card"><h3 className="mb-8">Rule categories</h3>
            <div className="grid g3">{ov.categories.map((c) => <div key={c.id} className="card soft row between"><b className="small">{c.label}</b><span className="badge">{c.count} rules</span></div>)}</div></div>
        </div>
      )}

      {tab === "rules" && rules && (
        <>
          <div className="row wrap gap-16 mb-16">
            <div className="seg"><button className={cat === "all" ? "on" : ""} onClick={() => setCat("all")}>All</button>{Object.entries(rules.categories).map(([k, l]) => <button key={k} className={cat === k ? "on" : ""} onClick={() => setCat(k)}>{l}</button>)}</div>
            <div className="grow" style={{ position: "relative", minWidth: 200 }}><Search size={16} style={{ position: "absolute", left: 12, top: 12, color: "var(--muted)" }} /><input className="input" style={{ paddingLeft: 36 }} placeholder="Search rules" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          </div>
          <div className="col">{shown.map((r) => <RuleCard key={r.id} r={r} />)}</div>
        </>
      )}

      {tab === "ontology" && (
        <div className="grid g2">
          <div className="card"><h3 className="mb-8">Health conditions</h3><div className="col gap-12">{ov.conditions.map((c) => <div key={c.id}><b>{c.label}</b><p className="small muted">{c.summary}</p><ul className="small muted" style={{ margin: "4px 0 0", paddingLeft: 18 }}>{c.guidelines.map((g) => <li key={g}>{g}</li>)}</ul></div>)}</div></div>
          <div className="col gap-20">
            <div className="card"><h3 className="mb-8">Eating styles</h3>{ov.diets.map((d) => <p key={d.id} className="small mb-8"><b>{titleCase(d.id)}</b> <span className="muted">{d.summary}</span></p>)}</div>
            <div className="card"><h3 className="mb-8">Allergens tracked</h3><div className="chips">{ov.allergens.map((a) => <span key={a} className="tag">{titleCase(a)}</span>)}</div></div>
            <div className="card"><h3 className="mb-8">How numbers become properties</h3><table className="tbl"><tbody>{ov.thresholds.map((t) => <tr key={t.property}><td><code className="mono">{t.property}</code></td><td className="small muted">{t.definition}</td></tr>)}</tbody></table></div>
          </div>
        </div>
      )}

      {tab === "foods" && (foods ? (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="tbl"><thead><tr><th>Food</th><th>kcal</th><th>Protein</th><th>GI</th><th>Derived properties</th></tr></thead>
            <tbody>{foods.map((f) => <tr key={f.id}><td className="bold">{f.name}</td><td>{f.calories}</td><td>{f.protein}</td><td>{f.glycemic_index ?? "-"}</td><td>{[...f.properties, ...f.contains.map((c) => `contains ${c}`)].map((p) => <span key={p} className="tag" style={{ marginRight: 4 }}>{p.replace("_", " ")}</span>)}</td></tr>)}</tbody></table>
        </div>) : <Loading />)}

      {tab === "play" && <Playground items={meals.map((m) => m.name)} />}
    </div>
  );
}
