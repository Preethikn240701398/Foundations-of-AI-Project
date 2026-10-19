import { useEffect, useState } from "react";
import { CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar, BarChart } from "recharts";
import { TrendingDown, TrendingUp, Users, Brain } from "lucide-react";
import api, { errText } from "../services/api";
import { useUI } from "../context/UIContext";
import { Empty, Loading, fmtDate, titleCase } from "../components/ui";

const tip = { contentStyle: { borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)" } };

export default function Progress() {
  const { toast } = useUI();
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/analytics/overview").then((r) => setD(r.data)).catch((e) => toast(errText(e), "err")); }, [toast]);
  if (!d) return <Loading text="Analysing your data..." />;

  const w = d.weights;
  const series = [...w.series.map((x) => ({ date: x.date, weight: x.weight })), ...w.forecast.map((x) => ({ date: x.date, forecast: x.weight }))];
  if (w.series.length && w.forecast.length) series[w.series.length - 1].forecast = w.series[w.series.length - 1].weight;
  const macro = d.intake.macro_avg;
  const pie = macro ? [["Protein", macro.protein * 4, "var(--protein)"], ["Carbs", macro.carbs * 4, "var(--carbs)"], ["Fat", macro.fat * 9, "var(--fat)"]].map(([name, value, color]) => ({ name, value, color })) : [];
  const trendUp = w.slope_per_week > 0;

  return (
    <div>
      <div className="page-head"><div><h1>Progress</h1><p>Trends learned from your own data using simple machine-learning models.</p></div></div>
      <div className="grid g4 mb-16">
        <div className="card"><div className="stat"><span className="v row gap-6">{w.series.length > 1 ? (trendUp ? <TrendingUp size={22} /> : <TrendingDown size={22} />) : null}{w.series.length > 1 ? `${w.slope_per_week > 0 ? "+" : ""}${w.slope_per_week}` : "-"}</span><span className="l">kg per week (regression)</span></div></div>
        <div className="card"><div className="stat"><span className="v">{w.eta_weeks ?? "-"}</span><span className="l">{w.target_weight ? `weeks to ${w.target_weight} kg` : "set a target weight in Profile"}</span></div></div>
        <div className="card"><div className="stat"><span className="v">{d.intake.adherence != null ? `${d.intake.adherence}%` : "-"}</span><span className="l">days within 15% of target</span></div></div>
        <div className="card"><div className="stat"><span className="v">{d.preferences.top.length}</span><span className="l">learned food preferences</span></div></div>
      </div>

      <div className="grid g2 mb-16">
        <div className="card">
          <div className="card-head"><h3>Weight trend &amp; forecast</h3><span className="tiny muted">{w.algorithm}</span></div>
          {w.series.length < 2 ? <Empty emoji="⚖️" title="Log at least two weigh-ins"><p className="small">Add your weight on the Dashboard to see a trend line and a 4-week forecast.</p></Empty> : (
            <div style={{ height: 280 }}><ResponsiveContainer><LineChart data={series}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tickFormatter={fmtDate} stroke="var(--muted)" tickLine={false} fontSize={12} /><YAxis domain={["dataMin - 1", "dataMax + 1"]} stroke="var(--muted)" tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip {...tip} labelFormatter={fmtDate} />
              {w.target_weight && <ReferenceLine y={w.target_weight} stroke="var(--fat)" strokeDasharray="5 4" />}
              <Line dataKey="weight" name="Weight" stroke="var(--primary)" strokeWidth={3} dot={{ r: 4 }} connectNulls />
              <Line dataKey="forecast" name="Forecast" stroke="var(--protein)" strokeWidth={2.5} strokeDasharray="6 5" dot={false} connectNulls /></LineChart></ResponsiveContainer></div>)}
        </div>
        <div className="card">
          <div className="card-head"><h3>Calories, last 14 days</h3></div>
          <div style={{ height: 280 }}><ResponsiveContainer><BarChart data={d.intake.series}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(x) => fmtDate(x)} stroke="var(--muted)" tickLine={false} fontSize={11} interval={2} /><YAxis stroke="var(--muted)" tickLine={false} axisLine={false} fontSize={12} />
            <Tooltip {...tip} labelFormatter={fmtDate} /><ReferenceLine y={d.intake.series[0]?.target} stroke="var(--fat)" strokeDasharray="5 4" />
            <Bar dataKey="calories" fill="var(--primary)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </div>
      </div>

      <div className="grid g3">
        <div className="card">
          <h3 className="mb-8">Macro balance (7-day average)</h3>
          {!macro ? <p className="small muted">Log meals to see your macro split.</p> : (<>
            <div style={{ height: 180 }}><ResponsiveContainer><PieChart><Pie data={pie} dataKey="value" innerRadius={48} outerRadius={78} paddingAngle={3} stroke="none">{pie.map((p) => <Cell key={p.name} fill={p.color} />)}</Pie><Tooltip {...tip} formatter={(v) => `${Math.round(v)} kcal`} /></PieChart></ResponsiveContainer></div>
            <div className="legend" style={{ justifyContent: "center" }}>{pie.map((p) => <span key={p.name}><i className="dot" style={{ background: p.color }} /> {p.name} {Math.round((p.value / pie.reduce((s, x) => s + x.value, 0)) * 100)}%</span>)}</div></>)}
        </div>
        <div className="card">
          <div className="card-head"><h3 className="row gap-6"><Brain size={18} />What you like</h3></div>
          {d.preferences.top.length === 0 ? <p className="small muted">Use 👍 / 👎 on meals. The system adjusts tag weights after each choice and ranks future meals with them.</p> : (
            <div className="col" style={{ gap: 10 }}>{[...d.preferences.top, ...d.preferences.bottom].map((p) => (
              <div key={p.tag} className="row"><span className="small grow">{titleCase(p.tag)}</span><span className={`badge ${p.weight >= 0 ? "good" : "avoid"}`}>{p.weight > 0 ? "+" : ""}{p.weight}</span></div>))}</div>)}
          <p className="tiny muted mt-12">{d.preferences.algorithm}</p>
        </div>
        <div className="card">
          <div className="card-head"><h3 className="row gap-6"><Users size={18} />People like you</h3></div>
          <p className="small muted mb-8">K-means grouped you with {d.cohort.members_count} sample profiles:</p>
          <div className="col gap-6">{d.cohort.members.map((m) => <div key={m.label} className="row between small"><b>{m.label}</b><span className="muted">{m.calories} kcal · BMI {m.bmi}</span></div>)}</div>
          <p className="tiny muted mt-12">{d.cohort.algorithm}. Sample cohort shown for illustration.</p>
        </div>
      </div>
    </div>
  );
}
