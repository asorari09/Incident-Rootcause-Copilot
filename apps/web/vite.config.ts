import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/scenarios": "http://127.0.0.1:8000",
      "/metrics": "http://127.0.0.1:8000",
      "/incidents": "http://127.0.0.1:8000",
      "/runbooks": "http://127.0.0.1:8000",
    },
  },
});
