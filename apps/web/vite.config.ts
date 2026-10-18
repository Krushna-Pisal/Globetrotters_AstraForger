import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In docker-compose the API is reachable as http://api:8000; locally as http://localhost:8000.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/v1": apiTarget,
      "/health": apiTarget,
    },
  },
});
