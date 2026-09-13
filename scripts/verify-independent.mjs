import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
const base = process.env.JOBFLY_URL || "http://127.0.0.1:8787";
const out =
  process.env.JOBFLY_VERIFY_DIR ||
  "/mnt/donto-data/donto-resources/research/jobfly-independent-v4/browser";
await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    process.env.CHROME_PATH ||
    "/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome",
  args: [
    "--no-sandbox",
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader-webgl",
  ],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage(),
  errors = [];
page.on("pageerror", (e) => errors.push(e.message));
let id;
const read = () =>
  page.evaluate(
    (id) => fetch(`/api/state?session=${id}`).then((r) => r.json()),
    id,
  );
async function until(test, seconds = 1200) {
  const deadline = Date.now() + seconds * 1000;
  while (Date.now() < deadline) {
    const state = await read();
    if (state.status === "error") throw Error(state.error);
    if (test(state)) return state;
    await page.waitForTimeout(1000);
  }
  throw Error("Swarm did not reach the required behavior");
}
try {
  for (let attempt = 0; ; attempt++) {
    try {
      const health = await fetch(`${base}/healthz`);
      if (health.ok) break;
    } catch {
      /* The container may still be starting. */
    }
    if (attempt >= 45) throw Error("Service did not become healthy");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  if (process.env.JOBFLY_SESSION_FILE) {
    ({ id } = JSON.parse(await fs.readFile(process.env.JOBFLY_SESSION_FILE, "utf8")));
    await page.goto(`${base}/s/${id}`);
    await fs.writeFile(`${out}/private-session.json`, JSON.stringify({ id }), { mode: 0o600 });
  } else {
  await page.goto(base);
  await page
    .getByRole("heading", { name: "Start with your resume." })
    .waitFor();
  assert.equal(await page.locator("canvas").count(), 0);
  await page.getByRole("button", { name: /Use thomasdavis resume/ }).click();
  await page
    .getByRole("heading", { name: "Looks like you?" })
    .waitFor({ timeout: 45000 });
  await page.getByRole("button", { name: "Find my jobs", exact: true }).click();
  await page.waitForURL(/\/s\/[a-f0-9]{48}$/, { timeout: 180000 });
  id = new URL(page.url()).pathname.split("/").pop();
  await fs.writeFile(`${out}/private-session.json`, JSON.stringify({ id }), {
    mode: 0o600,
  });
  }
  const first = await until((s) => s.status === "ready");
  console.log("Packaged brain ready; observing autonomous movement");
  assert(first.running);
  assert.equal(first.policyVersion, 4);
  assert.equal(first.ecosystem.sharedBrain, false);
  assert.equal(new Set(first.swarm.map(f => f.brainSteps)).size, 1);
  assert.equal(first.swarm.length, 24);
  const catalog = await page.evaluate(
    (id) => fetch(`/api/jobs?session=${id}`).then((r) => r.json()),
    id,
  );
  assert(catalog.jobs.length >= 500);
  assert(
    catalog.jobs.every(
      (j) => j.source !== "example" && /^https?:\/\//.test(j.url),
    ),
  );
  assert.equal(
    new Set(catalog.jobs.map((j) => j.url)).size,
    catalog.jobs.length,
  );
  const observed = await until(
    (s) =>
      s.ecosystem.explored >= 24 &&
      s.swarm.every(
        (f, i) =>
          Math.hypot(f.x - first.swarm[i].x, f.z - first.swarm[i].z) > 0.01,
      ),
  );
  if (process.env.JOBFLY_WAIT_FOR_DISCOVERIES === "1") {
    const discovery = await until(
      (s) => s.ecosystem.recommendations.length > 0,
      7200,
    );
    assert.equal(discovery.updates, 0);
    await fs.writeFile(
      `${out}/autonomous-discovery.json`,
      JSON.stringify(
        {
          elapsed: discovery.elapsed,
          explored: discovery.ecosystem.explored,
          recommendations: discovery.ecosystem.recommendations.length,
          landings: discovery.landings,
          ratings: discovery.updates,
        },
        null,
        2,
      ),
    );
    console.log("Suggestions surfaced without feedback");
  }
  assert(observed.running);
  assert.equal(observed.updates, 0);
  if (observed.elapsed < 120)
    assert.equal(observed.ecosystem.recommendations.length, 0);
  await page.getByLabel("Search all jobs").fill(catalog.jobs[0].company);
  await page.locator(".opportunity-list .job-chips button").first().click();
  await page
    .getByRole("button", { name: "I like this", exact: true })
    .waitFor();
  const selected = await page.locator(".job-summary h2").innerText();
  assert(
    !/<\/?(?:div|p|span|strong)\b/i.test(
      await page.locator(".job-summary > p").first().innerText(),
    ),
  );
  const reply = page.waitForResponse(
    (r) => r.url().includes("/api/feedback") && r.request().method() === "POST",
    { timeout: 120000 },
  );
  await page.getByRole("button", { name: "I like this", exact: true }).click();
  const reward = await (await reply).json();
  assert.equal(reward.changed, 0);
  const learned = await until((s) => s.updates === 1 && s.swarm.every(f => f.learningUpdates === 1));
  assert(learned.changed > 0);
  assert.equal(new Set(learned.swarm.map(f => f.brainSteps)).size, 1);
  assert.equal(learned.ecosystem.feedback[0].completed.length, 24);
  assert(learned.running);
  await until((s) => s.elapsed > learned.elapsed + .1);
  assert.equal(await page.locator(".job-summary h2").innerText(), selected);
  await page.getByLabel("Search all jobs").fill("");
  await page.waitForTimeout(1500);
  const renderer = await page
    .locator(".habitat canvas")
    .evaluate((c) => ({ ...c.dataset }));
  assert.equal(Number(renderer.jobs), catalog.jobs.length);
  assert.equal(Number(renderer.flies), 24);
  assert(Number(renderer.drawCalls) < 40);
  assert((await page.locator(".world-label").count()) <= 12);
  assert(
    (await page.locator(".opportunity-list .job-chips button").count()) <= 30,
  );
  await page.screenshot({ path: `${out}/swarm-desktop.png`, fullPage: true });
  await page.getByLabel("Inspect fly", { exact: true }).selectOption("23");
  await until(s => s.ecosystem.activeFly === 23);
  await page.getByRole("button", { name: "Brain", exact: true }).click();
  await page.getByLabel("Circuit intervention").selectOption("no_motor");
  const silenced = await until((s) => s.intervention === "no_motor");
  assert(!silenced.learning);
  await page.getByLabel("Circuit intervention").selectOption("intact");
  await until((s) => s.intervention === "intact");
  await page.screenshot({ path: `${out}/brain-desktop.png`, fullPage: true });
  await page.getByRole("button", { name: "Explore", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({ path: `${out}/swarm-mobile.png`, fullPage: true });
  const second = await browser.newPage();
  await second.goto(`${base}/s/${id}`);
  await second.waitForFunction(
    () => document.body.innerText.includes("1 ratings"),
    undefined,
    { timeout: 120000 },
  );
  const saved = await second.evaluate(
    (id) => fetch(`/api/resume.json?session=${id}`).then((r) => r.json()),
    id,
  );
  assert.equal(saved.basics.name, "Thomas Davis");
  await second.close();
  assert.deepEqual(errors, []);
  const results = {
    jobs: catalog.jobs.length,
    flies: 24,
    exploredWithoutFeedback: observed.ecosystem.explored,
    changedEdges: learned.changed,
    independentBrains: true,
    perBrainFeedbackCompleted: 24,
    selectionStable: true,
    reopened: true,
    mobile: true,
    renderer,
    errors,
  };
  await fs.writeFile(`${out}/results.json`, JSON.stringify(results, null, 2));
  await page.evaluate(id => fetch(`/api/control?session=${id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "pause" }) }), id);
  const checkpoint = await page.evaluate(id => fetch(`/api/diagnostics?session=${id}`).then(r => r.json()), id);
  assert.equal(checkpoint.brains.length, 24);
  assert.equal(new Set(checkpoint.brains.map(f => f.stateDigest)).size, 24);
  assert(checkpoint.brains.every(f => f.steps === checkpoint.worldSteps && f.learningUpdates === 1));
  await fs.writeFile(`${out}/before-restart.json`, JSON.stringify(checkpoint, null, 2));
  console.log(JSON.stringify(results));
} finally {
  await browser.close();
}
