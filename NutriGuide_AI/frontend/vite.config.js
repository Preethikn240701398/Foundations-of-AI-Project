import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API = process.env.VITE_API_URL || "http://127.0.0.1:8000";
const prefixes = ["auth", "profiles", "nutrition", "meals", "knowledge", "diet-plans", "tracker", "analytics",
  "chatbot", "food-scanner", "workout-planner", "ai-lab", "health"];

export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 700, rollupOptions: { output: { manualChunks: { charts: ["recharts"], vendor: ["react", "react-dom", "react-router-dom", "axios"] } } } },
  server: {
    port: 5173,
    proxy: Object.fromEntries(prefixes.map((p) => [`/api/${p}`, { target: API, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, "") }])),
  },
});
