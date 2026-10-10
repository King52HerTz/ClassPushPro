// Reproduce a browser carrying fresh old HTML, then navigate from the new cloud page.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('../private/qa-tools/node_modules/playwright');
const root = path.resolve(__dirname, '../website');
const seeded = new Set();
const mime = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const file = path.resolve(root, '.' + url.pathname);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
  if (['/index.html', '/download.html'].includes(url.pathname) && !url.search && !seeded.has(url.pathname)) {
    seeded.add(url.pathname);
    res.writeHead(200, { 'Content-Type': 'text/html', 'Cache-Control': 'max-age=604800' });
    res.end('<h1>OLD CACHED PAGE</h1>'); return;
  }
  res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
  fs.createReadStream(file).pipe(res);
});

async function main() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port;
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
  try {
    const page = await browser.newPage();
    for (const file of ['index.html', 'download.html', 'index.html']) {
      await page.goto(base + '/' + file);
      await page.getByText('OLD CACHED PAGE', { exact: true }).waitFor();
    }
    await page.goto(base + '/cloud.html');
    await page.locator('.nav-links').getByRole('link', { name: '首页', exact: true }).click();
    assert.ok(new URL(page.url()).searchParams.get('v'), 'home navigation must bypass pre-release HTML cache');
    await page.getByText('v3.0.0 · 正式发布 · 云端提醒与日历导出', { exact: true }).waitFor();
    await page.locator('.nav-links').getByRole('link', { name: '下载中心', exact: true }).click();
    assert.ok(new URL(page.url()).searchParams.get('v'), 'download navigation must bypass pre-release HTML cache');
    await page.getByRole('link', { name: '下载桌面版 v3.0.0' }).waitFor();
    await page.getByRole('link', { name: 'ClassPush 首页', exact: true }).click();
    await page.getByText('校园安排，带在身边', { exact: true }).waitFor();
    assert.equal(await page.getByText('OLD CACHED PAGE', { exact: true }).count(), 0);
    console.log('Warm-cache regression passed: cached old homepage/download seeded, new navigation/brand bypass cache and keep v3.0.0.');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(() => server.close());
