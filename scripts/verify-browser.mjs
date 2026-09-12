import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const base = process.env.JOBFLY_URL || 'http://127.0.0.1:8787';
const out = process.env.JOBFLY_VERIFY_DIR || '/mnt/donto-data/donto-resources/research/fly-jsonresume-20260912';
await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome', headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-angle=swiftshader-webgl'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const read = () => page.evaluate(() => fetch('/api/state').then(r => r.json()));
async function until(predicate, seconds = 120) {
  const end = Date.now() + seconds * 1000;
  while (Date.now() < end) { const state = await read(); if (predicate(state)) return state; await page.waitForTimeout(800); }
  throw new Error('Timed out waiting for live simulation.');
}
try {
  await page.goto(base);
  // Let the app establish its signed cookie before issuing test-side requests.
  await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent?.includes('Start exploring') && !b.disabled), undefined, { timeout: 120000 });
  console.log('Browser connected to its isolated brain.');
  await page.getByRole('button', { name: 'Start exploring', exact: true }).click();
  const landed = await until(s => s.landed !== null);
  console.log('Landed:', landed.landed);
  assert(landed.elapsed > 0 && landed.totalSpikes > 0);
  await page.getByLabel('Optional feedback reason').fill('Browser verification: this example is not for me.');
  const response = page.waitForResponse(r => r.url().endsWith('/api/feedback') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Not for me', exact: true }).click();
  const feedback = await (await response).json();
  assert(feedback.changed > 0, JSON.stringify(feedback));
  const learned = await until(s => s.updates === 1);
  assert(learned.preferences[landed.landed] < 0);
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  const paused = await until(s => !s.running);
  await page.waitForTimeout(600);
  assert.equal((await read()).elapsed, paused.elapsed);
  await page.getByRole('button', { name: 'Field notes', exact: true }).click();
  await page.getByText('Browser verification: this example is not for me.').waitFor();
  await page.getByRole('button', { name: 'Bring your resume', exact: true }).click();
  await page.getByRole('button', { name: 'Saved jobs', exact: true }).click();
  await page.locator('input[type=file]').setInputFiles({ name: 'jobs.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify([{ id: 'qa-import', title: 'Verification role', company: 'Test habitat', description: 'A synthetic import for verification.', location: 'Remote', source: 'example' }])) });
  await page.getByRole('dialog').waitFor({ state: 'hidden' });
  const imported = await page.evaluate(() => fetch('/api/jobs').then(r => r.json()));
  assert.equal(imported.jobs.length, 1);
  assert.equal(imported.jobs[0].id, 'qa-import');
  const rejected = await page.evaluate(() => fetch('/api/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ jobs: [{ id: 'broken' }] }) }).then(r => r.status));
  assert.equal(rejected, 400);
  await page.evaluate(() => fetch('/api/examples', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }));
  await page.getByRole('button', { name: 'The habitat', exact: true }).click();
  await page.reload();
  const restored = await until(s => s.status === 'ready');
  assert.equal(restored.updates, 1);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/jobfly-desktop-verified.png`, fullPage: true });
  await page.getByRole('button', { name: 'The brain', exact: true }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/jobfly-brain-verified.png`, fullPage: true });
  await page.getByRole('button', { name: 'The habitat', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(1500);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: `${out}/jobfly-mobile-verified.png`, fullPage: true });
  await context.storageState({ path: `${out}/browser-verification-session.json` });
  await fs.chmod(`${out}/browser-verification-session.json`, 0o600);
  assert.deepEqual(errors, []);
  const result = { landed: landed.landed, simulatedSecondsToLand: landed.elapsed, changedEdges: feedback.changed, learnedPreference: learned.preferences[landed.landed], import: 'passed', pause: 'passed', reloadPersistence: 'passed', errors };
  await fs.writeFile(`${out}/browser-verification.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally { await browser.close(); }
