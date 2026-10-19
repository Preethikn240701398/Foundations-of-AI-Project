import { X, ShieldCheck, ShieldAlert, ThumbsUp, Ban } from "lucide-react";

export const VERDICT = {
  recommended: { label: "Great match", cls: "good", icon: ThumbsUp },
  neutral: { label: "Okay", cls: "neutral", icon: ShieldCheck },
  caution: { label: "Occasionally", cls: "caution", icon: ShieldAlert },
  avoid: { label: "Avoid", cls: "avoid", icon: Ban },
};

export function VerdictBadge({ verdict }) {
  const v = VERDICT[verdict] || VERDICT.neutral;
  const Icon = v.icon;
  return <span className={`badge ${v.cls}`}><Icon size={12} />{v.label}</span>;
}

export function Spinner({ size = 18 }) {
  return <span className="spinner" style={{ width: size, height: size }} />;
}

export function Loading({ text = "Loading..." }) {
  return <div className="empty"><Spinner size={26} /><p className="mt-12">{text}</p></div>;
}

export function Empty({ emoji = "🥗", title, children }) {
  return <div className="empty"><div className="big">{emoji}</div><h3 style={{ color: "var(--text)" }}>{title}</h3><div className="mt-8">{children}</div></div>;
}

export function Modal({ title, onClose, children, wide }) {
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={wide ? { width: "min(900px,100%)" } : null}>
        <div className="row between mb-16">
          <h2>{title}</h2>
          <button className="btn ghost icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Ring({ value, max, size = 170, stroke = 14, color = "var(--primary)", children }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.min(Math.max(value / (max || 1), 0), 1);
  const over = value > max;
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={over ? "var(--danger)" : color} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} style={{ transition: "stroke-dashoffset .6s cubic-bezier(.2,.8,.2,1)" }} />
      </svg>
      <div className="ring-center">{children}</div>
    </div>
  );
}

export function MacroBar({ label, value, target, unit = "g", color }) {
  const pct = Math.min(100, Math.round((value / (target || 1)) * 100));
  return (
    <div className="macro-row">
      <span className="bold">{label}</span>
      <div className="bar"><i style={{ width: `${pct}%`, background: color }} /></div>
      <span className="val">{Math.round(value)}<span className="muted"> / {Math.round(target)}{unit}</span></span>
    </div>
  );
}

export function MacroPills({ m }) {
  return (
    <div className="macro-pills">
      <span className="mp p">P {Math.round(m.protein)}g</span>
      <span className="mp c">C {Math.round(m.carbs)}g</span>
      <span className="mp f">F {Math.round(m.fat)}g</span>
    </div>
  );
}

export function Field({ label, hint, children }) {
  return <div className="field"><label>{label}</label>{children}{hint && <span className="hint">{hint}</span>}</div>;
}

export function Chips({ options, value, onChange, multi = true, labels = {} }) {
  const toggle = (o) => {
    if (!multi) return onChange(o);
    onChange(value.includes(o) ? value.filter((x) => x !== o) : [...value, o]);
  };
  return (
    <div className="chips">
      {options.map((o) => {
        const on = multi ? value.includes(o) : value === o;
        return <button type="button" key={o} className={`chip ${on ? "on" : ""}`} onClick={() => toggle(o)}>{labels[o] || o}</button>;
      })}
    </div>
  );
}

export function Seg({ options, value, onChange }) {
  return (
    <div className="seg">
      {options.map(([v, l]) => <button type="button" key={v} className={value === v ? "on" : ""} onClick={() => onChange(v)}>{l}</button>)}
    </div>
  );
}

export function BmiGauge({ bmi }) {
  const min = 15, max = 40;
  const pos = Math.min(Math.max(((bmi - min) / (max - min)) * 100, 1), 99);
  const seg = [
    { w: ((18.5 - min) / (max - min)) * 100, c: "#60a5fa" },
    { w: ((25 - 18.5) / (max - min)) * 100, c: "#34c07e" },
    { w: ((30 - 25) / (max - min)) * 100, c: "#fbbf24" },
    { w: ((max - 30) / (max - min)) * 100, c: "#f87171" },
  ];
  return (
    <div style={{ position: "relative", paddingTop: 22 }}>
      <div style={{ display: "flex", height: 10, borderRadius: 99, overflow: "hidden", gap: 2 }}>
        {seg.map((s, i) => <div key={i} style={{ width: `${s.w}%`, background: s.c }} />)}
      </div>
      <div style={{ position: "absolute", top: 0, left: `${pos}%`, transform: "translateX(-50%)", textAlign: "center" }}>
        <div style={{ fontSize: 11, fontWeight: 800, background: "var(--text)", color: "var(--bg)", borderRadius: 6, padding: "1px 6px" }}>{bmi}</div>
        <div style={{ width: 2, height: 9, background: "var(--text)", margin: "0 auto" }} />
      </div>
      <div className="row between tiny muted mt-4"><span>15</span><span>18.5</span><span>25</span><span>30</span><span>40</span></div>
    </div>
  );
}

export const fmtDate = (iso) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
export const titleCase = (s) => String(s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
