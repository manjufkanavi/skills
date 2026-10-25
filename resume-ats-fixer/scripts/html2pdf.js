// HTML → A4 PDF via Playwright Chromium (auto-detects cached browser + lib).
// Usage: node html2pdf.js <input.html> <output.pdf>
const fs = require('fs');
const os = require('os');
const path = require('path');

function findPlaywright() {
  const candidates = [
    'playwright-core',
    path.join(os.homedir(), '.hermes/node_modules/playwright-core'),
    '/opt/homebrew/lib/node_modules/@playwright/mcp/node_modules/playwright-core',
    '/usr/local/lib/node_modules/@playwright/mcp/node_modules/playwright-core',
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_) { /* try next */ }
  }
  console.error('FAIL: playwright-core not found (npm i -g @playwright/mcp or set NODE_PATH)');
  process.exit(1);
}

function findChromium() {
  const cache = path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright');
  if (!fs.existsSync(cache)) return null;
  const revs = fs.readdirSync(cache)
    .filter(d => d.startsWith('chromium-') && !d.includes('headless'))
    .sort().reverse();
  for (const r of revs) {
    for (const arch of ['chrome-mac-arm64', 'chrome-mac-x64']) {
      const exe = path.join(cache, r, arch, 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing');
      if (fs.existsSync(exe)) return exe;
    }
  }
  return null; // let Playwright use its own registry copy
}

const [input, output] = [process.argv[2], process.argv[3]];
if (!input || !output) {
  console.error('Usage: node html2pdf.js <input.html> <output.pdf>');
  process.exit(2);
}

(async () => {
  const chromium = findPlaywright().chromium;
  const exe = findChromium();
  const browser = await chromium.launch({
    ...(exe ? { executablePath: exe } : {}),
    args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--no-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
  await page.goto('file://' + path.resolve(input), { waitUntil: 'networkidle' });
  await page.pdf({
    path: output, preferCssPageSize: true, printBackground: true,
    width: '210mm', height: '297mm',
    margin: { top: '0', bottom: '0', left: '0', right: '0' },
  });
  await browser.close();
  console.log('PDF written:', output);
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
