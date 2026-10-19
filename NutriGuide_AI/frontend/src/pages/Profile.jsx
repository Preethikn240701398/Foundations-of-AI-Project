import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import api, { errText } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";
import { BodySection, EMPTY_PROFILE, GoalSection, HealthSection, RequirementsPreview, toPayload, useOptions } from "../components/ProfileForm";
import { Field, Seg, Spinner } from "../components/ui";

export default function Profile() {
  const { profile, setProfile } = useAuth();
  const { toast } = useUI();
  const opts = useOptions();
  const [v, setV] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!profile) return;
    const hc = Array.isArray(profile.health_condition) ? profile.health_condition : String(profile.health_condition || "").split(",").map((s) => s.trim()).filter((s) => s && s !== "none");
    setV({ ...EMPTY_PROFILE, ...profile, health_condition: hc, target_weight: profile.target_weight ?? "", custom_calories: profile.custom_calories ?? "" });
  }, [profile?.id]);
  if (!v) return null;
  const set = (patch) => setV((x) => ({ ...x, ...patch }));

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/profiles/me", toPayload(v));
      setProfile(data);
      toast("Profile updated. Targets recalculated.");
    } catch (e) { toast(errText(e), "err"); } finally { setBusy(false); }
  };

  return (
    <div>
      <div className="page-head">
        <div><h1>My profile</h1><p>Everything the system knows about you. Changing it recalculates your targets and safety rules.</p></div>
        <button className="btn" onClick={save} disabled={busy}>{busy ? <Spinner /> : <><Save size={16} />Save changes</>}</button>
      </div>
      <div className="two-col">
        <div className="col gap-20">
          <div className="card"><h3 className="mb-16">Body</h3><BodySection v={v} set={set} /></div>
          <div className="card"><h3 className="mb-16">Activity & goal</h3><GoalSection v={v} set={set} opts={opts} /></div>
          <div className="card"><h3 className="mb-16">Health & preferences</h3>
            <HealthSection v={v} set={set} opts={opts} extra={
              <Field label="Workout split">
                <Seg value={v.workout_split} onChange={(workout_split) => set({ workout_split })} options={[["full_body", "Full body"], ["upper_lower", "Upper / lower"], ["push_pull", "Push / pull / legs"]]} />
              </Field>} />
            <div className="divider" />
            <Field label="Custom calorie target (optional)" hint="Leave empty to use the calculated value. Allergy and health rules still apply.">
              <input className="input" type="number" min="1000" max="6000" step="50" value={v.custom_calories} onChange={(e) => set({ custom_calories: e.target.value })} placeholder="Auto" />
            </Field>
          </div>
        </div>
        <div className="sticky-col"><RequirementsPreview profile={v} /></div>
      </div>
    </div>
  );
}
