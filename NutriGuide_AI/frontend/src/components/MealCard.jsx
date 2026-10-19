import { Clock, Flame, Leaf, Info } from "lucide-react";
import { MacroPills, VerdictBadge } from "./ui";

export default function MealCard({ meal, onClick, actions, showSlot, compact }) {
  const clickable = !!onClick;
  return (
    <div className={`card meal-card ${clickable ? "click" : ""}`} onClick={onClick}>
      <div className="row" style={{ alignItems: "flex-start" }}>
        <div className="meal-emoji">{meal.emoji || "🍽️"}</div>
        <div className="grow">
          {showSlot && <div className="slot-label">{showSlot}</div>}
          <h3 style={{ fontSize: 16 }}>{meal.name}</h3>
          <div className="row gap-6 wrap small muted mt-4">
            <span className="row gap-4"><Flame size={13} />{meal.calories} kcal{meal.portion && meal.portion !== 1 ? ` · ${meal.portion}x` : ""}</span>
            {meal.prep_minutes && <span className="row gap-4"><Clock size={13} />{meal.prep_minutes} min</span>}
            {meal.glycemic_index != null && <span>GI {meal.glycemic_index}</span>}
          </div>
        </div>
        {meal.verdict && <VerdictBadge verdict={meal.verdict} />}
      </div>
      <MacroPills m={meal} />
      {!compact && meal.why?.length > 0 && (
        <div className="col gap-4">
          {meal.why.slice(0, 2).map((w, i) => (
            <div className="why" key={i}><Info size={13} /><span><b>{w.rule}</b> {w.text}</span></div>
          ))}
        </div>
      )}
      {!compact && meal.cuisine && (
        <div className="row gap-6 wrap">
          <span className="tag">{meal.cuisine}</span>
          {(meal.tags || []).filter((t) => ["vegan", "vegetarian", "fiber", "millet", "omega3"].includes(t)).slice(0, 3).map((t) => (
            <span className="tag" key={t}>{t === "vegan" ? <><Leaf size={10} /> vegan</> : t.replace("_", " ")}</span>
          ))}
        </div>
      )}
      {actions && <div className="row wrap" onClick={(e) => e.stopPropagation()}>{actions}</div>}
    </div>
  );
}
