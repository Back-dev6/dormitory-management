import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: /api được chuyển tiếp sang FastAPI (cổng 8000), nên không dính CORS
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
