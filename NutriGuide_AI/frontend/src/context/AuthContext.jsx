import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "../services/api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("ng_user")); } catch { return null; }
  });
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem("ng_token"));

  const refreshProfile = useCallback(async () => {
    const { data } = await api.get("/profiles/me");
    setProfile(data);
    return data;
  }, []);

  useEffect(() => {
    if (!localStorage.getItem("ng_token")) { setLoading(false); return; }
    refreshProfile().catch(() => {}).finally(() => setLoading(false));
  }, [refreshProfile]);

  const start = (session) => {
    localStorage.setItem("ng_token", session.access_token);
    localStorage.setItem("ng_user", JSON.stringify({ id: session.user.id, email: session.user.email }));
    setUser({ id: session.user.id, email: session.user.email });
    return refreshProfile();
  };
  const logout = () => {
    localStorage.removeItem("ng_token");
    localStorage.removeItem("ng_user");
    setUser(null); setProfile(null);
  };

  return <Ctx.Provider value={{ user, profile, setProfile, refreshProfile, start, logout, loading }}>{children}</Ctx.Provider>;
}
