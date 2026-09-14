import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api to the FastAPI backend during local dev (`npm run dev`).
// Set VITE_API_BASE at build time if the backend is deployed elsewhere.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:7860",
    },
  },
});
