// Public release and tutorial checks. No school login, cloud binding, or real sends.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('../private/qa-tools/node_modules/playwright');
const origin = process.env.CLASSPUSH_SITE_ORIGIN || 'http://127.0.0.1:5175';

async function main() {
  const release = await (await fetch(origin + '/version.json', { cache: 'no-store' })).json();
  assert.equal(release.version, '3.0.0');
  assert.equal(release.available, true);
  assert.equal(release.lanzou_url, release.download_url); // legacy clients
  assert.equal(typeof release.changelog, 'string');
  assert.ok(release.changelog.includes('中文安装'));
  assert.equal(new URL(release.download_url).hostname, 'classpush.eliauk312.top');
  const installer = fs.readFileSync(path.resolve(__dirname, '../private/packages/ClassPush_Setup_3.0.0.exe'));
  assert.equal(installer.length, release.size_bytes);
  assert.equal(crypto.createHash('sha256').update(installer).digest('hex'), release.sha256);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    for (const width of [375, 812, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(origin + '/calendar.html');
      const images = page.locator('main img');
      assert.equal(await images.count(), 7);
      for (const image of await images.all()) {
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(img => img.decode());
        assert.ok(await image.evaluate(img => img.naturalWidth > 0));
        assert.ok(await image.getAttribute('alt'));
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `tutorial overflow at ${width}`);
      for (const link of await page.locator('.guide-jumps a').all()) {
        assert.equal(await page.locator(await link.getAttribute('href')).count(), 1);
      }
      await page.screenshot({ path: path.resolve(__dirname, `../private/qa-output/calendar-guide-${width}.png`), fullPage: true });
    }
    await page.goto(origin + '/download.html');
    const download = page.getByRole('link', { name: '下载桌面版 v3.0.0' });
    await download.waitFor();
    assert.equal(await download.getAttribute('href'), release.download_url);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
  console.log('Release checks passed: 3.0.0/legacy manifest fields, installer size/SHA256, direct server download, seven tutorial images at 375/812/1280px. No real account operations.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
