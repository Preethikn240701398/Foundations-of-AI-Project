import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Leaf, ShieldCheck, Brain, CalendarCheck } from "lucide-react";
import api, { errText } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Field, Spinner } from "../components/ui";

function Art() {
  return (
    <div className="auth-art">
      <div className="brand" style={{ color: "#fff", padding: 0 }}><span className="brand-mark" style={{ background: "rgba(255,255,255,.2)" }}><Leaf size={19} /></span>NutriGuide AI</div>
      <div>
        <h1>Eat well, with reasons you can read.</h1>
        <p style={{ opacity: 0.85, marginTop: 14, maxWidth: 440, fontSize: 17 }}>A knowledge-based nutrition assistant that calculates your needs, applies expert rules and builds a safe, personalised diet plan.</p>
        <div className="col mt-24" style={{ gap: 14, opacity: 0.95 }}>
          <div className="row"><ShieldCheck size={20} /> Allergy and medical rules are never broken</div>
          <div className="row"><Brain size={20} /> Every decision comes with an explanation</div>
          <div className="row"><CalendarCheck size={20} /> 7-day plans in a single click</div>
        </div>
      </div>
      <div className="small" style={{ opacity: 0.7 }}>Educational project. Not a substitute for medical advice.</div>
    </div>
  );
}

function AuthForm({ mode }) {
  const isReg = mode === "register";
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const { start } = useAuth();
  const nav = useNavigate();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const { data } = await api.post(isReg ? "/auth/register" : "/auth/login", form);
      const p = await start(data);
      nav(p.onboarded ? "/app" : "/onboarding");
    } catch (ex) { setErr(errText(ex)); } finally { setBusy(false); }
  };

  return (
    <div className="auth-wrap">
      <Art />
      <div className="auth-form">
        <form className="auth-card" onSubmit={submit}>
          <div><h1>{isReg ? "Create your account" : "Welcome back"}</h1>
            <p className="muted mt-4">{isReg ? "It takes about a minute to personalise your plan." : "Log in to see today's plan."}</p></div>
          {isReg && <Field label="Your name"><input className="input" required value={form.name} onChange={set("name")} placeholder="Alex" /></Field>}
          <Field label="Email"><input className="input" type="email" required value={form.email} onChange={set("email")} placeholder="you@example.com" /></Field>
          <Field label="Password" hint={isReg ? "At least 6 characters" : null}><input className="input" type="password" required minLength={6} value={form.password} onChange={set("password")} /></Field>
          {err && <div className="banner bad">{err}</div>}
          <button className="btn lg block" disabled={busy}>{busy ? <Spinner /> : isReg ? "Create account" : "Log in"}</button>
          <p className="small muted center">
            {isReg ? <>Already have an account? <Link to="/login" className="bold" style={{ color: "var(--primary)" }}>Log in</Link></>
              : <>New here? <Link to="/register" className="bold" style={{ color: "var(--primary)" }}>Create an account</Link></>}
          </p>
          <p className="center small"><Link to="/" className="muted">← Back to home</Link></p>
        </form>
      </div>
    </div>
  );
}

export const Login = () => <AuthForm mode="login" />;
export const Register = () => <AuthForm mode="register" />;
