import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";

const Ctx = createContext(null);
export const useUI = () => useContext(Ctx);

export function UIProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem("ng_theme") || (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ng_theme", theme);
  }, [theme]);

  const toast = useCallback((text, type = "ok") => {
    const id = Math.random();
    setToasts((t) => [...t, { id, text, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200);
  }, []);

  return (
    <Ctx.Provider value={{ theme, toggleTheme: () => setTheme((t) => (t === "dark" ? "light" : "dark")), toast }}>
      {children}
      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type === "err" ? "err" : ""}`}>
            {t.type === "err" ? <AlertTriangle size={17} /> : <CheckCircle2 size={17} />}{t.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
