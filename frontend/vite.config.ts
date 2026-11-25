import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1", strictPort: true,
      headers: {
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws://127.0.0.1:* ws://localhost:*; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
      },
      port: Number(env.FRONTEND_PORT || 5173),
      proxy: { "/api": { target: `http://127.0.0.1:${env.BACKEND_PORT || 8000}`, changeOrigin: true } },
    },
  };
});
