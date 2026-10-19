import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, CalendarDays, UtensilsCrossed, Dumbbell, ScanLine, MessageCircle, BookOpenCheck,
  LineChart, FlaskConical, UserRound, Moon, Sun, Menu, LogOut, Leaf,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useUI } from "../context/UIContext";

const NAV = [
  { label: "Plan", items: [
    { to: "/app", end: true, icon: LayoutDashboard, text: "Dashboard" },
    { to: "/app/plan", icon: CalendarDays, text: "Diet plan" },
    { to: "/app/meals", icon: UtensilsCrossed, text: "Meals" },
    { to: "/app/workouts", icon: Dumbbell, text: "Workouts" },
  ] },
  { label: "Intelligence", items: [
    { to: "/app/assistant", icon: MessageCircle, text: "Assistant" },
    { to: "/app/scanner", icon: ScanLine, text: "Food scanner" },
    { to: "/app/knowledge", icon: BookOpenCheck, text: "Knowledge base" },
  ] },
  { label: "Insights", items: [
    { to: "/app/progress", icon: LineChart, text: "Progress" },
    { to: "/app/lab", icon: FlaskConical, text: "AI Lab" },
  ] },
];

export default function Layout() {
  const [open, setOpen] = useState(false);
  const { profile, logout } = useAuth();
  const { theme, toggleTheme } = useUI();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const initial = (profile?.name || "U")[0].toUpperCase();

  return (
    <div className="shell">
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand"><span className="brand-mark"><Leaf size={19} /></span>NutriGuide AI</div>
        {NAV.map((g) => (
          <div key={g.label}>
            <div className="nav-label">{g.label}</div>
            {g.items.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} onClick={() => setOpen(false)}>
                <n.icon size={19} />{n.text}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="sidebar-foot">
          <NavLink to="/app/profile" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} onClick={() => setOpen(false)}>
            <UserRound size={19} />My profile
          </NavLink>
          <div className="user-chip">
            <div className="avatar">{initial}</div>
            <div className="grow"><div className="bold small" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{profile?.name || "You"}</div>
              <div className="tiny muted">{profile?.requirements?.calories ?? "-"} kcal / day</div></div>
            <button className="btn ghost icon-btn" onClick={toggleTheme} title="Toggle theme">{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</button>
            <button className="btn ghost icon-btn" onClick={() => { logout(); nav("/"); }} title="Log out"><LogOut size={17} /></button>
          </div>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <button className="btn ghost icon-btn" onClick={() => setOpen(true)} aria-label="Menu"><Menu size={21} /></button>
          <div className="brand" style={{ padding: 0 }}><span className="brand-mark" style={{ width: 28, height: 28 }}><Leaf size={16} /></span>NutriGuide AI</div>
          <button className="btn ghost icon-btn" onClick={toggleTheme}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</button>
        </div>
        <div className="page fade-in" key={pathname}><Outlet /></div>
      </div>
    </div>
  );
}
