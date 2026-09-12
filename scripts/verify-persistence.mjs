import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base=process.env.JOBFLY_URL||'http://127.0.0.1:8787';
const out=process.env.JOBFLY_VERIFY_DIR||'/mnt/donto-data/donto-resources/research/fly-jsonresume-20260912/light-verification';
const {id}=JSON.parse(await fs.readFile(`${out}/private-session.json`,'utf8'));
// systemd activation can precede the Python server becoming ready.
for (let attempt=0; attempt<30; attempt++) {
 try { if ((await fetch(`${base}/healthz`)).ok) break; } catch { /* Startup window. */ }
 if(attempt===29) throw new Error('Server did not become healthy after restart.');
 await new Promise(resolve=>setTimeout(resolve,1000));
}
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome',args:['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader-webgl']});
try {
 const page=await browser.newPage();await page.goto(`${base}/s/${id}`);
 await page.waitForFunction(()=>document.body.innerText.includes('1 ratings'),undefined,{timeout:120000});
 const state=await page.evaluate(id=>fetch(`/api/state?session=${id}`).then(r=>r.json()),id);
 assert.equal(state.updates,1);assert(Object.values(state.marks).includes('liked'));
 const resume=await page.evaluate(id=>fetch(`/api/resume.json?session=${id}`).then(r=>r.json()),id);assert.equal(resume.basics.name,'Thomas Davis');
 const response=await page.request.get(`${base}/api/resume.json?session=${'a'.repeat(48)}`);assert.equal(response.status(),404);
 await fs.writeFile(`${out}/persistence-results.json`,JSON.stringify({updates:state.updates,marks:state.marks,resumeRestored:true,invalidLinkRejected:true},null,2));
 console.log('Session URL, resume, learning, and feedback survived restart.');
} finally {await browser.close();}
