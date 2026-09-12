import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base=process.env.JOBFLY_URL||'http://127.0.0.1:8787';
const out=process.env.JOBFLY_VERIFY_DIR||'/mnt/donto-data/donto-resources/research/fly-jsonresume-20260912/light-verification';
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome',args:['--no-sandbox']});
try {
 const page=await browser.newPage();
 page.on("response",r=>{if(r.url().includes("/api/convert")) console.log("Conversion HTTP",r.status());});
 await page.setContent('<h1>Alex Example</h1><h2>Software Engineer</h2><p>Work: Example Studio, Frontend Engineer, 2021–2025.</p><p>Built accessible React and TypeScript web applications.</p><p>Education: Example University, Bachelor of Computer Science, 2020.</p>');
 const pdf=await page.pdf(); console.log("PDF generated",pdf.length);
 await page.goto(base);
 await page.getByLabel('Upload resume file',{exact:true}).setInputFiles({name:'resume.pdf',mimeType:'application/pdf',buffer:pdf});
 await Promise.race([page.getByRole('heading',{name:'Looks like you?'}).waitFor({timeout:200000}), page.getByRole('alert').waitFor({timeout:200000}).then(async()=>{throw Error(await page.getByRole('alert').innerText());})]);
 const data=JSON.parse(await page.locator('#resume-json').inputValue());
 assert.equal(data.basics.name,'Alex Example');assert(data.work.some(w=>w.name.includes('Example Studio')));
 assert(data.education.some(e=>e.institution.includes('Example University')));
 const download=page.waitForEvent('download');await page.getByLabel('Download resume.json',{exact:true}).click();
 const file=await download;assert.equal(file.suggestedFilename(),'resume.json');
 await page.screenshot({path:`${out}/converted-resume.png`,fullPage:true});
 await page.getByRole('button',{name:'Choose another resume'}).click();
 await page.getByLabel('Upload resume file',{exact:true}).setInputFiles({name:'resume.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
 await page.getByRole('heading',{name:'Looks like you?'}).waitFor();
 assert.deepEqual(JSON.parse(await page.locator('#resume-json').inputValue()),data);
 await fs.writeFile(`${out}/upload-results.json`,JSON.stringify({pdf:'passed',jsonRoundTrip:'passed',download:'passed'},null,2));
 console.log('PDF → validated JSON Resume → review → download → JSON re-upload passed.');
} finally {await browser.close();}
