import { useEffect, useState } from "react";
import api from "../services/api";
import { BmiGauge, Chips, Field, Seg, titleCase } from "./ui";
import { AlertTriangle, Calculator } from "lucide-react";

export const EMPTY_PROFILE = {
  name: "", age: 25, sex: "female", height_cm: 165, weight: 65, target_weight: "", activity_level: "light",
  goal: "balanced", life_stage: "adult", health_condition: [], allergies: [], dietary_restrictions: [],
  meals_per_day: 4, workout_split: "full_body", custom_calories: "",
};

export function toPayload(p) {
  return {
    ...p,
    age: Number(p.age), height_cm: Number(p.height_cm), weight: Number(p.weight),
    target_weight: p.target_weight === "" || p.target_weight == null ? null : Number(p.target_weight),
    custom_calories: p.custom_calories === "" || p.custom_calories == null ? null : Number(p.custom_calories),
    meals_per_day: Number(p.meals_per_day),
  };
}

export function useOptions() {
  const [opts, setOpts] = useState(null);
  useEffect(() => { api.get("/nutrition/options").then((r) => setOpts(r.data)); }, []);
  return opts;
}

export function BodySection({ v, set }) {
  return (
    <div className="col gap-16">
      <Field label="What should we call you?"><input className="input" value={v.name} onChange={(e) => set({ name: e.target.value })} placeholder="Your name" /></Field>
      <div className="grid g2">
        <Field label="Age"><input className="input" type="number" min="10" max="100" value={v.age} onChange={(e) => set({ age: e.target.value })} /></Field>
        <Field label="Sex" hint="Used by the BMR equation"><Seg value={v.sex} onChange={(sex) => set({ sex })} options={[["female", "Female"], ["male", "Male"], ["other", "Other"]]} /></Field>
        <Field label="Height (cm)"><input className="input" type="number" min="100" max="230" value={v.height_cm} onChange={(e) => set({ height_cm: e.target.value })} /></Field>
        <Field label="Weight (kg)"><input className="input" type="number" min="25" max="300" step="0.1" value={v.weight} onChange={(e) => set({ weight: e.target.value })} /></Field>
      </div>
      <Field label="Target weight (optional)" hint="Used to estimate how long your goal will take"><input className="input" type="number" step="0.1" value={v.target_weight ?? ""} onChange={(e) => set({ target_weight: e.target.value })} placeholder="e.g. 60" /></Field>
    </div>
  );
}

export function GoalSection({ v, set, opts }) {
  if (!opts) return null;
  return (
    <div className="col gap-20">
      <Field label="How active are you?">
        <div className="choice-grid">
          {opts.activity_levels.map((a) => (
            <button type="button" key={a.id} className={`choice ${v.activity_level === a.id ? "on" : ""}`} onClick={() => set({ activity_level: a.id })}>
              <b>{a.label}</b><span className="small muted">{a.hint}</span>
            </button>
          ))}
        </div>
      </Field>
      <Field label="What is your goal?">
        <div className="choice-grid">
          {[["weight_loss", "Lose weight", "Gentle calorie deficit, more fibre"], ["balanced", "Stay balanced", "Maintain weight and eat well"],
            ["muscle_gain", "Build muscle", "Calorie surplus with high protein"], ["weight_gain", "Gain weight", "Energy-dense, nutritious meals"]].map(([id, t, d]) => (
            <button type="button" key={id} className={`choice ${v.goal === id ? "on" : ""}`} onClick={() => set({ goal: id })}>
              <b>{t}</b><span className="small muted">{d}</span>
            </button>
          ))}
        </div>
      </Field>
    </div>
  );
}

export function HealthSection({ v, set, opts, extra }) {
  if (!opts) return null;
  const condLabels = Object.fromEntries(opts.conditions.map((c) => [c.id, c.label]));
  return (
    <div className="col gap-20">
      <Field label="Health conditions" hint="Rules for these conditions are applied to every recommendation">
        <Chips options={opts.conditions.map((c) => c.id)} labels={condLabels} value={v.health_condition} onChange={(health_condition) => set({ health_condition })} />
      </Field>
      <Field label="Allergies"><Chips options={opts.allergens} value={v.allergies} onChange={(allergies) => set({ allergies })} labels={Object.fromEntries(opts.allergens.map((a) => [a, titleCase(a)]))} /></Field>
      <Field label="Eating style" hint="Pick any that apply">
        <Chips options={opts.diets.map((d) => d.id)} value={v.dietary_restrictions} onChange={(dietary_restrictions) => set({ dietary_restrictions })} labels={Object.fromEntries(opts.diets.map((d) => [d.id, titleCase(d.id)]))} />
      </Field>
      <div className="grid g2">
        <Field label="Life stage"><select className="input" value={v.life_stage} onChange={(e) => set({ life_stage: e.target.value })}>{opts.life_stages.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></Field>
        <Field label="Meals per day"><Seg value={String(v.meals_per_day)} onChange={(m) => set({ meals_per_day: Number(m) })} options={[["3", "3 meals"], ["4", "3 + snack"]]} /></Field>
      </div>
      {extra}
    </div>
  );
}

export function RequirementsPreview({ profile, compact }) {
  const [req, setReq] = useState(null);
  useEffect(() => {
    const t = setTimeout(() => {
      api.post("/nutrition/preview", toPayload(profile)).then((r) => setReq(r.data)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [JSON.stringify(profile)]);
  if (!req) return <div className="card"><p className="muted">Calculating...</p></div>;
  return (
    <div className="card">
      <div className="row between"><h3 className="row gap-6"><Calculator size={18} />Your daily needs</h3><span className={`badge ${req.bmi_category === "normal" ? "good" : req.bmi_category === "underweight" ? "neutral" : "caution"}`}>{req.bmi_label}</span></div>
      <div className="mt-12"><BmiGauge bmi={req.bmi} /></div>
      <div className="grid g2 mt-16" style={{ gap: 12 }}>
        <div className="stat"><span className="v">{req.calories}</span><span className="l">kcal / day target</span></div>
        <div className="stat"><span className="v">{req.protein_g}g</span><span className="l">protein</span></div>
        <div className="stat"><span className="v">{req.carbs_g}g</span><span className="l">carbohydrate</span></div>
        <div className="stat"><span className="v">{req.fat_g}g</span><span className="l">fat</span></div>
      </div>
      <div className="small muted mt-12">Healthy weight for your height: <b>{req.healthy_weight_min}-{req.healthy_weight_max} kg</b> · Water ≈ {(req.water_ml / 1000).toFixed(1)} L · Fibre {req.fiber_g} g</div>
      {req.warnings.map((w) => <div key={w} className="banner warn mt-12"><AlertTriangle size={17} style={{ flex: "none" }} />{w}</div>)}
      {!compact && (
        <>
          <div className="divider" />
          <h4 className="mb-8">How we calculated it</h4>
          <div className="col gap-4">{req.steps.map((s, i) => <div key={i} className="mono muted">{s}</div>)}</div>
        </>
      )}
    </div>
  );
}
