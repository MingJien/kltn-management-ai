import { defineConfig } from "@playwright/test";
import path from "node:path";

if (!process.env.KLTN_E2E_RUN_DIR || !process.env.KLTN_E2E_ACCOUNTS_JSON) {
  throw new Error("Run from the repository root: python -m tools.run_e2e (isolated test database required)");
}
const webPort = process.env.KLTN_E2E_WEB_PORT || "5174";
const webUrl = `http://127.0.0.1:${webPort}`;
export default defineConfig({
  testDir: "./e2e", fullyParallel: false, workers: 1,
  timeout: 90000, expect: {timeout: 10000}, retries: 0,
  reporter: "list", outputDir: path.join(process.env.KLTN_E2E_RUN_DIR, "browser-results"),
  use: {baseURL:webUrl, browserName:"chromium", headless:true,
    viewport:{width:1440,height:1000}, trace:"off", screenshot:"only-on-failure"},
  webServer: {command:`npm run dev -- --host 127.0.0.1 --port ${webPort} --strictPort`,
    url:webUrl, reuseExistingServer:false, timeout:30000},
});
