import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const BACKEND = "http://127.0.0.1:7432";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/web/",
  build: {
    outDir: "../web",
    emptyOutDir: true,
  },
  server: {
    port: 5183,
    proxy: [
      { context: ["/host", "/guest", "/project", "/file", "/text", "/cursor", "/disconnect", "/session", "/peers", "/dialog"], target: BACKEND, changeOrigin: true },
      { context: "/ws", target: BACKEND, ws: true, changeOrigin: true },
    ],
  },
});
