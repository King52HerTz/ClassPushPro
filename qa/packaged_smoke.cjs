// Launch only the candidate binary; close only its process tree after inspection.
// No school queries, credentials, real message sends, or existing app termination.
const { spawn, execFileSync } = require('node:child_process');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '../private/qa-tools/node_modules/playwright');
const exe = process.env.CLASSPUSH_CANDIDATE_EXE
  ? path.resolve(process.env.CLASSPUSH_CANDIDATE_EXE)
  : path.resolve(__dirname, '../private/dist-3.0.0/ClassPush/ClassPush.exe');
const port = 19393;
const child = spawn(exe, [], {
  cwd: path.dirname(exe), windowsHide: true,
  env: { ...process.env,
    WEBVIEW2_USER_DATA_FOLDER: path.resolve(__dirname, '../private/qa-output/webview-candidate'),
    WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${port} --remote-debugging-address=127.0.0.1` },
  stdio: 'ignore',
});

async function main() {
  let browser;
  for (let attempt = 0; attempt < 60; attempt++) {
    if (child.exitCode !== null) throw new Error('Candidate exited before UI inspection');
    try { browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 1000 }); break; }
    catch { await new Promise(resolve => setTimeout(resolve, 500)); }
  }
  assert.ok(browser, 'WebView2 debugging connection unavailable');
  try {
    const page = browser.contexts()[0].pages()[0];
    await page.getByRole('menuitem', { name: '云端推送' }).waitFor({ timeout: 20000 });
    await page.getByRole('menuitem', { name: '日历导出' }).waitFor();
    const centered = await page.locator('.sidebar-toggle').evaluate(button => {
      const toggle = button.getBoundingClientRect(), sidebar = button.closest('.workspace-sidebar').getBoundingClientRect();
      return Math.abs(toggle.x + toggle.width / 2 - sidebar.x - sidebar.width / 2) < 1;
    });
    assert.equal(centered, true, 'packaged sidebar toggle is centered');
    assert.equal(await page.evaluate(() => typeof window.pywebview.api.get_config), 'function');
    const response = await page.request.get(page.url());
    assert.equal(response.status(), 200);
    await page.screenshot({ path: path.resolve(__dirname, '../private/qa-output/packaged-app.png'), fullPage: true, mask: [page.locator('input')] });
    console.log('Packaged UI passed: real WebView2 rendering, navigation, bridge, local HTTP 200. No school queries or sends.');
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(() => {
  if (child.exitCode === null && child.pid) {
    try { execFileSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true }); } catch {}
  }
});
