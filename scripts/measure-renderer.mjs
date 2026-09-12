import { chromium } from "@playwright/test";
import fs from "node:fs/promises";
const root = "/mnt/donto-data/donto-resources/research/jobfly-neural-v2";
const { id } = JSON.parse(
  await fs.readFile(`${root}/browser/private-session.json`, "utf8"),
);
const browser = await chromium.launch({
  executablePath:
    "/home/ajax/.agent-browser/browsers/chrome-150.0.7871.24/chrome",
  args: [
    "--no-sandbox",
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader-webgl",
  ],
});
try {
  const page = await browser.newPage({
    viewport: { width: 1280, height: 1000 },
  });
  await page.goto(`http://127.0.0.1:8787/s/${id}`);
  await page.waitForFunction(
    () => document.querySelector(".habitat canvas")?.dataset.flies === "24",
    undefined,
    { timeout: 120000 },
  );
  await page.locator(".habitat").scrollIntoViewIfNeeded();
  const report = await page.evaluate(async () => {
    const times = [],
      start = performance.now();
    await new Promise((resolve) => {
      function frame(now) {
        times.push(now);
        if (now - start < 12000) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
    return {
      fps: (times.length - 1) / ((times.at(-1) - times[0]) / 1000),
      frames: times.length,
      visible: document.visibilityState,
      renderer: { ...document.querySelector(".habitat canvas").dataset },
    };
  });
  await page.screenshot({ path: `${root}/browser/render-optimized.png` });
  await fs.writeFile(`${root}/renderer.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
}
