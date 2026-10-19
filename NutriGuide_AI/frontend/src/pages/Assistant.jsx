import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Send, Sparkles, Trash2 } from "lucide-react";
import api, { errText } from "../services/api";
import { useUI } from "../context/UIContext";
import { TraceBlock } from "../components/ReasoningTrace";
import { MacroPills, Spinner, VerdictBadge } from "../components/ui";

const SUGGESTIONS = ["Is chicken biryani okay for me?", "Suggest a breakfast", "What is my BMI?", "Can I eat samosa?", "Suggest a snack", "Make me a weekly plan"];

function BotMessage({ m }) {
  return (
    <div className="bubble bot">
      <div className="row gap-6 mb-8"><Bot size={16} color="var(--primary)" /><b className="small">NutriGuide</b></div>
      <p>{m.summary}</p>
      {m.item && (
        <div className="card soft mt-12 row wrap" style={{ padding: 12 }}>
          <span style={{ fontSize: 28 }}>{m.item.emoji || "🍽️"}</span>
          <div className="grow"><b>{m.item.name}</b><div className="tiny muted">{m.item.calories} kcal · GI {m.item.glycemic_index ?? "n/a"}</div></div>
          <VerdictBadge verdict={m.item.verdict} />
        </div>
      )}
      {m.items?.length > 0 && (
        <div className="col mt-12">{m.items.map((it) => (
          <div key={it.id || it.name} className="card soft row" style={{ padding: 10 }}>
            <span style={{ fontSize: 24 }}>{it.emoji}</span>
            <div className="grow"><b className="small">{it.name}</b><div className="tiny muted">{it.calories} kcal</div><MacroPills m={it} />
              {it.why?.[0] && <div className="tiny muted mt-4"><b>{it.why[0].rule}</b> {it.why[0].text}</div>}</div>
            <VerdictBadge verdict={it.verdict} />
          </div>))}
        </div>
      )}
      {m.requirements && (
        <div className="grid g2 mt-12" style={{ gap: 8 }}>
          {[["BMI", m.requirements.bmi], ["BMR", `${m.requirements.bmr} kcal`], ["TDEE", `${m.requirements.tdee} kcal`], ["Target", `${m.requirements.calories} kcal`]].map(([l, v]) => (
            <div key={l} className="card soft" style={{ padding: 10 }}><div className="tiny muted">{l}</div><b>{v}</b></div>))}
        </div>
      )}
      {m.link && <Link to={m.link.to} className="btn sm mt-12">{m.link.label}</Link>}
      <TraceBlock trace={m.trace} proof={m.proof} />
    </div>
  );
}

export default function Assistant() {
  const { toast } = useUI();
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);

  useEffect(() => {
    api.get("/chatbot/history").then((r) => setMsgs(r.data.flatMap((h) => [{ role: "me", text: h.query }, { role: "bot", ...h }]))).catch(() => {});
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (q = text) => {
    if (!q.trim() || busy) return;
    setText(""); setMsgs((m) => [...m, { role: "me", text: q }]); setBusy(true);
    try { const { data } = await api.post("/chatbot/query", { query: q }); setMsgs((m) => [...m, { role: "bot", ...data }]); }
    catch (e) { toast(errText(e), "err"); } finally { setBusy(false); }
  };
  const clear = async () => { await api.delete("/chatbot/history"); setMsgs([]); };

  return (
    <div>
      <div className="page-head">
        <div><h1>Assistant</h1><p>Ask about any food. Answers come from the rule engine, and you can open the reasoning behind each one.</p></div>
        {msgs.length > 0 && <button className="btn ghost sm" onClick={clear}><Trash2 size={14} />Clear chat</button>}
      </div>
      <div className="card chat">
        <div className="chat-scroll">
          {msgs.length === 0 && (
            <div className="empty"><div className="big">💬</div><h3 style={{ color: "var(--text)" }}>How can I help?</h3>
              <p className="small mt-8">I check foods against your allergies, diet, health conditions and goal.</p>
              <div className="chips mt-16" style={{ justifyContent: "center" }}>{SUGGESTIONS.map((s) => <button key={s} className="chip" onClick={() => send(s)}><Sparkles size={13} />{s}</button>)}</div></div>
          )}
          {msgs.map((m, i) => m.role === "me" ? <div key={i} className="bubble me">{m.text}</div> : <BotMessage key={i} m={m} />)}
          {busy && <div className="bubble bot row"><Spinner /><span className="muted small">Reasoning...</span></div>}
          <div ref={end} />
        </div>
        <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask e.g. “Is paneer tikka wrap okay for me?”" />
          <button className="btn" disabled={busy || !text.trim()}><Send size={16} />Send</button>
        </form>
      </div>
    </div>
  );
}
