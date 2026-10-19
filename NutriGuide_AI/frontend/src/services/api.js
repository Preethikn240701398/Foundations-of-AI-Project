import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "/api" });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("ng_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !err.config.url.startsWith("/auth/")) {
      localStorage.removeItem("ng_token");
      localStorage.removeItem("ng_user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const errText = (e) => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join(", ");
  return e?.message || "Something went wrong";
};

export default api;
