import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const directory = process.env.JOBFLY_VERIFY_DIR || '/mnt/donto-data/donto-resources/research/fly-jsonresume-20260912/public-verification';
const base = process.env.JOBFLY_URL || 'https://fly.jsonresume.org';
for (let attempt = 0; attempt < 30; attempt++) {
  const healthy = await fetch(`${base}/healthz`).then(r => r.ok).catch(() => false);
  if (healthy) break;
  if (attempt === 29) throw new Error('Origin did not become ready after restart.');
  await new Promise(resolve => setTimeout(resolve, 1000));
}
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome', args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader-webgl'] });
try {
  const a = await browser.newContext({ storageState: `${directory}/browser-verification-session.json`, viewport: { width: 1440, height: 1100 } });
  const page = await a.newPage();
  await page.goto(base);
  await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent?.includes('Start exploring') && !b.disabled), undefined, { timeout: 120000 });
  const restored = await (await a.request.get(`${base}/api/state`)).json();
  assert.equal(restored.updates, 1);
  assert.equal(restored.marks['example-11'], 'passed');
  assert(restored.preferences['example-11'] < 0);
  const b = await browser.newContext();
  // Sequential bootstrap establishes the second cookie before further requests.
  const fresh = await (await b.request.get(`${base}/api/state`)).json();
  assert.equal(fresh.updates, 0);
  assert.deepEqual(fresh.marks, {});
  const freshJobs = await (await b.request.get(`${base}/api/jobs`)).json();
  assert(freshJobs.jobs.every(j => j.source === 'example'));
  const denied = await a.request.post(`${base}/api/control`, { headers: { Origin: 'https://unrelated.example' }, data: { action: 'play' } });
  assert.equal(denied.status(), 403);
  const cookie = (await a.cookies()).find(c => c.name === 'jobfly_session');
  assert(cookie.httpOnly && cookie.secure && cookie.sameSite === 'Strict');
  await page.getByRole('button', { name: 'The brain', exact: true }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${directory}/jobfly-brain-final.png`, fullPage: true });
  await page.getByRole('button', { name: 'The habitat', exact: true }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${directory}/jobfly-desktop-final.png`, fullPage: true });
  const report = { restartPersistence: 'passed', separateBrowserState: 'passed', crossSiteMutation: 'rejected', cookieFlags: 'HttpOnly; Secure; SameSite=Strict', restoredUpdates: restored.updates, restoredPreference: restored.preferences['example-11'] };
  await fs.writeFile(`${directory}/persistence-verification.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
} finally { await browser.close(); }
