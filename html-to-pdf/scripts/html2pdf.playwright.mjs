// Playwright headless Chromium HTML→PDF.
//
// Prefer this over WeasyPrint when you need CSS page-break, background colors,
// @page size/margins, or per-section pages (each section = one PDF page).
//
// One-time setup (install the browser once per machine):
//   npx playwright-core@latest install chromium
//
// Usage:
//   node scripts/html2pdf.playwright.mjs input.html output.pdf [Letter|A4] [JSON-margin]
//
//   JSON-margin (optional 4th arg), e.g.:
//   '{"top":"0.72in","bottom":"0.85in","left":"1in","right":"1in"}'
//
// Exits non-zero and prints the error if conversion fails.

import { chromium } from 'playwright-core';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';

const htmlPath = process.argv[2] || '/tmp/report.html';
const pdfPath  = process.argv[3] || '/tmp/report.pdf';
const format   = (process.argv[4] || 'Letter').toUpperCase();

let margin = { top: '0.72in', bottom: '0.85in', left: '1in', right: '1in' };
if (process.argv[5]) margin = JSON.parse(process.argv[5]);

const abs = path.resolve(htmlPath);
const url = pathToFileURL(abs).href;

let browser;
try {
  browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400); // let fonts/layout settle

  await page.pdf({
    path: pdfPath,
    format,
    printBackground: true,
    preferCssPageSize: true, // honor @page size instead of forcing viewport
    margin,
  });

  const size = fs.statSync(pdfPath).size;
  console.log(`WROTE ${pdfPath} (${size} bytes)`);
} catch (err) {
  console.error('HTML→PDF failed:', err.message);
  process.exit(1);
} finally {
  if (browser) await browser.close();
}
