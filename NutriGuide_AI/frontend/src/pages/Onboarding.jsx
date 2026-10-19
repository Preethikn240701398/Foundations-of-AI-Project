import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Leaf, Sparkles } from "lucide-react";
import api, { errText } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import { BodySection, EMPTY_PROFILE, GoalSection, HealthSection, RequirementsPreview, toPayload, useOptions } from "../components/ProfileForm";
import { Spinner } from "../components/ui";

const STEPS = [
  ["About you", "Tell us a little about yourself so we can calculate your body metrics."],
  ["Lifestyle & goal", "Your activity and goal decide how many calories you need."],
  ["Health & preferences", "Allergies and conditions become hard safety rules for every meal."],
];

export default function Onboarding() {
  const { profile, setProfile, refreshProfile } = useAuth();
  const { toast } = useUI();
  const nav = useNavigate();
  const opts = useOptions();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [v, setV] = useState({ ...EMPTY_PROFILE, name: profile?.name && profile.name !== "Friend" ? profile.name : "" });
  const set = (patch) => setV((x) => ({ ...x, ...patch }));

  const finish = async () => {
    setBusy(true);
    try {
      await api.put("/profiles/me", toPayload({ ...v, name: v.name || "Friend" }));
      await refreshProfile();
      toast("Profile saved. Let's build your plan!");
      nav("/app/plan?welcome=1");
    } catch (e) { toast(errText(e), "err"); setBusy(false); }
  };

  return (
    <div style={{ minHeight: "100%", padding: "28px 18px 60px" }}>
      <div style={{ maxWidth: 1060, margin: "0 auto" }}>
        <div className="brand" style={{ padding: "0 0 18px" }}><span className="brand-mark"><Leaf size={19} /></span>NutriGuide AI</div>
        <div className="two-col">
          <div className="card">
            <div className="stepper">{STEPS.map((_, i) => <i key={i} className={i <= step ? "done" : ""} />)}</div>
            <div className="eyebrow">Step {step + 1} of {STEPS.length}</div>
            <h1>{STEPS[step][0]}</h1>
            <p className="muted mt-4 mb-16">{STEPS[step][1]}</p>
            {step === 0 && <BodySection v={v} set={set} />}
            {step === 1 && <GoalSection v={v} set={set} opts={opts} />}
            {step === 2 && <HealthSection v={v} set={set} opts={opts} />}
            <div className="row between mt-24">
              <button className="btn secondary" disabled={step === 0} onClick={() => setStep(step - 1)}><ArrowLeft size={16} />Back</button>
              {step < STEPS.length - 1
                ? <button className="btn" onClick={() => setStep(step + 1)}>Continue<ArrowRight size={16} /></button>
                : <button className="btn" onClick={finish} disabled={busy}>{busy ? <Spinner /> : <><Sparkles size={16} />Create my plan</>}</button>}
            </div>
          </div>
          <div className="sticky-col"><RequirementsPreview profile={v} compact={step < 2} /></div>
        </div>
      </div>
    </div>
  );
}
