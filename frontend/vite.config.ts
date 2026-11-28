import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

declare const process: { env: { KLTN_E2E_RUN_DIR?: string } };
const e2eRunDir = process.env.KLTN_E2E_RUN_DIR;

export default defineConfig({
  plugins: [react()],
  cacheDir: e2eRunDir ? `${e2eRunDir}/vite-cache` : undefined,
  server: {
    host: "127.0.0.1",
    port: 1573,
    strictPort: true,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
});
