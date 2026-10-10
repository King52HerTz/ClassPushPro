// Synthetic-data UI smoke test. Does not contact the school or send real messages.
const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '../private/qa-tools/node_modules/playwright');

const repo = path.resolve(__dirname, '..');
const output = path.join(repo, 'private/qa-output');
fs.mkdirSync(output, { recursive: true });
const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const desktop = name.startsWith('/desktop/');
  const root = path.join(repo, desktop ? 'RestoredSource/frontend/dist' : 'website');
  const file = path.resolve(root, '.' + (desktop ? name.slice(8) : name));
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end('not found'); return; }
  res.writeHead(200, { 'Content-Type': (types[path.extname(file)] || 'application/octet-stream') + ';charset=utf-8' });
  fs.createReadStream(file).pipe(res);
});

async function main() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port;
  const browser = await chromium.launch({ headless: true, ...(process.env.EDGE_PATH ? { executablePath: process.env.EDGE_PATH } : {}) });
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  page.on('pageerror', error => errors.push(error.message));
  let loggedIn = false;
  let account = { username: '20260001', uid: 'UID***001', morning: false, evening: false, grades: false, paused: true, notice: '', needs_auth: false, jobs: [] };
  await page.route('**/api/cloud/**', async route => {
    const suffix = new URL(route.request().url()).pathname.replace('/api/cloud', '');
    const method = route.request().method();
    let status = 200, result = { message: '测试操作成功' };
    if (suffix === '/account' && method === 'GET') { status = loggedIn ? 200 : 401; result = loggedIn ? account : { message: '请先登录云端管理' }; }
    if (suffix === '/auth/request') result = { challenge: 'FAKE_CHALLENGE_ONLY', message: '测试验证码已发送' };
    if (suffix === '/auth/confirm') loggedIn = true;
    if (suffix === '/account' && method === 'PATCH') account = { ...account, ...route.request().postDataJSON() };
    if (suffix === '/account' && method === 'DELETE') loggedIn = false;
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(result) });
  });
  await page.goto(base + '/cloud.html');
  await page.locator('#login-panel:not([hidden])').waitFor();
  await page.locator('#username').fill('20260001');
  await page.locator('#password').fill('FAKE_PASSWORD_ONLY');
  await page.locator('#uid').fill('UID_FAKEUSER00001');
  await page.locator('#consent').check();
  await page.locator('#login-form button').click();
  await page.locator('#code-form:not([hidden])').waitFor();
  await page.locator('#code').fill('123456');
  await page.locator('#code-form button[type=submit]').click();
  await page.locator('#account-panel:not([hidden])').waitFor();
  await page.locator('#evening').check();
  await page.locator('#paused').uncheck();
  await page.locator('#settings-form button').click();
  await page.locator('#feedback.success').waitFor();
  assert.equal(account.evening, true);
  assert.equal(account.paused, false);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.screenshot({ path: path.join(output, 'cloud-mobile.png'), fullPage: true });
  page.on('dialog', dialog => dialog.accept());
  await page.locator('#delete').click();
  await page.locator('#login-panel:not([hidden])').waitFor();
  const desktop = await browser.newPage({ viewport: { width: 1200, height: 850 } });
  desktop.on('pageerror', error => errors.push(error.message));
  await desktop.addInitScript(() => {
    const result = data => Promise.resolve({ status: 'success', data });
    const preview = { currentWeek: 7, semesterName: '2026-2027-1', weekOneMonday: '2026-08-31', scheduleStatus: 'active', source: 'online', availableWeeks: [2, 3, 7], courses: [{ courseName: '测试课程（合成数据）', weekday: 1, xqmc: '星期一', classTime: '1-2', startNode: 1, endNode: 2, classWeekDetails: '2,3,7', classWeek: '2-7周', location: '测试教室', teacherName: '测试教师' }] };
    const config = { username: '20260001', has_password: true, calendar_alarm_minutes: 15, time_slots: { '1-2': ['08:30', '10:05'], '3-4': ['10:25', '12:00'] } };
    window.pywebview = { api: {
      get_config: () => result(config), get_preview_courses: () => result(preview),
      save_config: () => result(null),
      export_calendar_ics: () => result({ file_path: 'TEST_DOWNLOAD/classpush.ics', course_count: 3 }),
      get_grade_semesters: () => result({ current_term: { semester_id: '2026-2027-1', semester_name: '2026-2027-1' }, selected_semester: { semester_id: '2026-2027-1', semester_name: '2026-2027-1' }, semester_list: [{ semester_id: '2026-2027-1', semester_name: '2026-2027-1' }], grades: [] }),
      open_cloud_portal: () => result(null), open_calendar_guide: () => result(null),
    } };
  });
  await desktop.goto(base + '/desktop/index.html');
  await desktop.getByText('课表随身，电脑不用一直开着').waitFor();
  await desktop.getByRole('menuitem', { name: '日历导出' }).click();
  await desktop.getByText('2026-08-31', { exact: true }).waitFor();
  await desktop.getByRole('button', { name: '导出 ICS 文件' }).click();
  await desktop.getByText('TEST_DOWNLOAD/classpush.ics').waitFor();
  await desktop.screenshot({ path: path.join(output, 'desktop-calendar.png'), fullPage: true });
  await desktop.getByRole('menuitem', { name: '课表预览' }).click();
  await desktop.getByText('测试课程（合成数据）', { exact: true }).first().waitFor();
  await desktop.getByRole('menuitem', { name: '云端推送' }).click();
  await desktop.getByRole('button', { name: '打开官网云端管理' }).waitFor();
  const site = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  site.on('pageerror', error => errors.push(error.message));
  await site.goto(base + '/index.html');
  await site.getByText('v3.0.0 · 云端版验收候选').waitFor();
  await site.screenshot({ path: path.join(output, 'website-home.png'), fullPage: true });
  await site.goto(base + '/download.html');
  await site.getByText('新版安装包待验收').waitFor();
  assert.equal(await site.locator('.changelog-list li').count(), 6);
  assert.deepEqual(errors, []);
  await browser.close();
  console.log('UI smoke passed: mobile binding/settings/deletion, desktop calendar/course/cloud, website version/download. Synthetic data only.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(() => server.close());
