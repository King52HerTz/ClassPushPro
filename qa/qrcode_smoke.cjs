// Anonymous image rendering only; does not subscribe, log in, or send messages.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '../private/qa-tools/node_modules/playwright');
const origin = process.env.QR_TEST_ORIGIN || 'https://classpush.eliauk312.top';

async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.EDGE_PATH ? { executablePath: process.env.EDGE_PATH } : {}) });
  try {
    for (const width of [375, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const violations = [];
      await page.exposeFunction('recordCspViolation', directive => violations.push(directive));
      await page.addInitScript(() => document.addEventListener('securitypolicyviolation', event => window.recordCspViolation(event.violatedDirective)));
      await page.goto(origin + '/cloud.html');
      await page.locator('#uid-help summary').click();
      const qr = page.locator('#uid-help .qr');
      await qr.scrollIntoViewIfNeeded();
      await qr.evaluate(img => img.decode());
      assert.equal(await qr.evaluate(img => img.complete && img.naturalWidth > 0), true);
      const src = await qr.evaluate(img => img.src);
      assert.equal(new URL(src).origin, new URL(origin).origin);
      assert.equal((await page.request.get(src)).status(), 200);
      assert.equal(await qr.locator('..').getAttribute('href'), 'assets/wxpusher/hnit-subscribe.jpg');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.deepEqual(violations, []);
      await page.close();
    }
  } finally { await browser.close(); }
  console.log('QR PASS: same-origin image decoded on mobile/desktop, original-image link, no CSP violations. No subscription or messages sent.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
