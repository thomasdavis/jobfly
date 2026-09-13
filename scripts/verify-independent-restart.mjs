import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
const base = process.env.JOBFLY_URL || "http://127.0.0.1:8789";
const out = process.env.JOBFLY_VERIFY_DIR || "/mnt/donto-data/donto-resources/research/jobfly-independent-v4/candidate-browser";
const { id } = JSON.parse(await fs.readFile(`${out}/private-session.json`, "utf8"));
const before = JSON.parse(await fs.readFile(`${out}/before-restart.json`, "utf8"));
const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || "/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome",
  args: ["--no-sandbox", "--enable-unsafe-swiftshader", "--use-angle=swiftshader-webgl"],
});
try {
  const page = await browser.newPage();
  for (let attempt = 0; ; attempt++) {
    try { if ((await fetch(`${base}/healthz`)).ok) break; } catch {}
    if (attempt > 90) throw Error("HTTP readiness failed");
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  // Home has no event stream: restoration must not advance even one world tick.
  await page.goto(base);
  let state;
  for (let attempt = 0; ; attempt++) {
    state = await page.evaluate(id => fetch(`/api/state?session=${id}`).then(r => r.json()), id);
    if (state.status === "error") throw Error(state.error);
    if (state.status === "ready") break;
    if (attempt > 600) throw Error("Brain restoration timed out");
    await page.waitForTimeout(1000);
  }
  const after = await page.evaluate(id => fetch(`/api/diagnostics?session=${id}`).then(r => r.json()), id);
  assert.equal(after.checkpointDigest, before.checkpointDigest);
  assert.deepEqual(after.brains, before.brains);
  assert.equal(after.worldSteps, before.worldSteps);
  assert.equal(after.modelSignature, before.modelSignature);
  assert.equal(after.brains.length, 24);
  const resume = await page.evaluate(id => fetch(`/api/resume.json?session=${id}`).then(r => r.json()), id);
  assert.equal(resume.basics.name, "Thomas Davis");
  await page.goto(`${base}/s/${id}`);
  await page.getByLabel("Inspect fly", { exact: true }).waitFor();
  await page.getByLabel("Inspect fly", { exact: true }).selectOption("7");
  await page.waitForFunction(id => fetch(`/api/state?session=${id}`).then(r => r.json()).then(s => s.ecosystem?.activeFly === 7), id);
  const result = { exactReplay: true, independentBrains: 24, steps: after.worldSteps,
    modelSignature: after.modelSignature, checkpointDigest: after.checkpointDigest,
    resumeRestored: true, inspectorWorks: true };
  await fs.writeFile(`${out}/restart-results.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
