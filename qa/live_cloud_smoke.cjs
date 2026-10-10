// Anonymous production checks only. Never logs in, binds a user, or sends messages.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '../private/qa-tools/node_modules/playwright');
const origin = 'https://classpush.eliauk312.top';

async function main() {
  const redirect = await fetch(origin.replace('https:', 'http:') + '/cloud.html', { redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), origin + '/cloud.html');
  const health = await fetch(origin + '/api/cloud/health');
  assert.equal(health.status, 200);
  assert.equal((await health.json()).version, '3.0.2');
  const account = await fetch(origin + '/api/cloud/account');
  assert.equal(account.status, 401);
  const crossOrigin = await fetch(origin + '/api/cloud/auth/request', {
    method: 'POST', headers: { Origin: 'https://example.invalid', 'Content-Type': 'application/json' }, body: '{}',
  });
  assert.equal(crossOrigin.status, 403);
  for (const file of ['/', '/index.html', '/download.html']) {
    const response = await fetch(origin + file, { method: 'HEAD' });
    assert.equal(response.status, 200);
    assert.match(response.headers.get('cache-control') || '', /no-store/, `HTML cache policy: ${file}`);
  }
  const browser = await chromium.launch({ headless: true, ...(process.env.EDGE_PATH ? { executablePath: process.env.EDGE_PATH } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/cloud.html');
    await page.locator('#login-panel:not([hidden])').waitFor();
    await page.getByRole('button', { name: '验证教务并发送 App 验证码' }).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(errors, []);
    await page.screenshot({ path: path.resolve(__dirname, '../private/qa-output/live-cloud-login.png'), fullPage: true });
    await page.getByRole('button', { name: '打开导航', exact: true }).click();
    await page.locator('.nav-links').getByRole('link', { name: '首页', exact: true }).click();
    assert.ok(new URL(page.url()).searchParams.get('v'));
    await page.getByText('v3.0.2 · 正式发布 · 云端提醒与日历导出', { exact: true }).waitFor();
    await page.getByRole('button', { name: '打开导航', exact: true }).click();
    await page.locator('.nav-links').getByRole('link', { name: '下载中心', exact: true }).click();
    assert.ok(new URL(page.url()).searchParams.get('v'));
    await page.getByRole('link', { name: '下载桌面版 v3.0.2' }).waitFor();
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
  console.log('Live anonymous checks passed: HTTPS/API protection, HTML cache policy, mobile cloud -> homepage -> v3 download navigation. No real business operations.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
