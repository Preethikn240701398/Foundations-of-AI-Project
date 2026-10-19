import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

const TYPE_LABEL = { derive: "DERIVE", reject: "REJECT", caution: "CAUTION", prefer: "PREFER" };

function Rule({ text }) {
  const parts = text.split(/(\bIF\b|\bAND\b|\bNOT\b|->|\bTHEN\b)/g);
  return <>{parts.map((p, i) => (/^(IF|AND|NOT|->|THEN)$/.test(p) ? <span key={i} className="kw">{p}</span> : p))}</>;
}

export function Facts({ facts = [], derived = [] }) {
  return (
    <div>
      {facts.map((f) => <span key={f} className="fact">{f}</span>)}
      {derived.map((f) => <span key={f} className="fact new" title="derived by the engine">+ {f}</span>)}
    </div>
  );
}

export function FiredRules({ fired = [] }) {
  if (!fired.length) return <p className="muted small">No rule fired, so the engine has no objection.</p>;
  return (
    <div className="trace">
      {fired.map((f, i) => (
        <div key={i} className={`fire ${f.type}`}>
          <div className="rid">{f.rule_id}</div>
          <div>
            <div className="bold">{f.text} <span className="tiny muted">· cycle {f.cycle} · {TYPE_LABEL[f.type]}{f.weight ? ` ${f.type === "prefer" ? "+" : "-"}${f.weight}` : ""}</span></div>
            <div className="rule-text"><Rule text={`IF ${f.if}  ->  THEN ${f.adds || f.then}`} /></div>
            {f.because?.length > 0 && <div className="tiny muted mt-4">because {f.because.join(", ")}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function Proof({ node }) {
  if (!node) return null;
  return (
    <div className="proof-node">
      <b>{node.goal}</b>
      <div className="by">{node.by}</div>
      {node.children?.length > 0 && <div className="proof mt-4">{node.children.map((c, i) => <Proof key={i} node={c} />)}</div>}
    </div>
  );
}

export function TraceBlock({ trace, proof, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  if (!trace) return null;
  return (
    <div className="mt-12">
      <button className="btn ghost sm" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />} How I decided (inference trace)
      </button>
      {open && (
        <div className="col gap-16 mt-8 fade-in">
          <div><h4 className="mb-8">1 · Known facts &amp; derived facts</h4><Facts facts={trace.facts} derived={trace.derived} /></div>
          <div><h4 className="mb-8">2 · Forward chaining (rules that fired)</h4><FiredRules fired={trace.fired} /></div>
          {proof && <div><h4 className="mb-8">3 · Backward chaining (proof of the verdict)</h4><Proof node={proof} /></div>}
        </div>
      )}
    </div>
  );
}
