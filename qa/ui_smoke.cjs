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
let activeBrowser;

async function main() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port;
  const browser = activeBrowser = await chromium.launch({ headless: true, ...(process.env.EDGE_PATH ? { executablePath: process.env.EDGE_PATH } : {}) });
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
  assert.equal(await page.getByText('工作空间', { exact: false }).count(), 0);
  await page.getByText('你的云端学习空间', { exact: true }).waitFor();
  await page.locator('#login-panel:not([hidden])').waitFor();
  await page.screenshot({ path: path.join(output, 'cloud-login-mobile.png'), fullPage: true });
  assert.equal(await page.getByText('微信', { exact: false }).count(), 0);
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
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile cloud overflow');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: path.join(output, 'cloud-mobile.png'), fullPage: true });
  page.on('dialog', dialog => dialog.accept());
  await page.locator('.account-details > summary').click();
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
      save_config: data => { window.__savedCalendarConfig = data; return result(null); },
      export_calendar_ics: () => result({ file_path: 'TEST_DOWNLOAD/classpush.ics', course_count: 3 }),
      get_grade_semesters: () => result({ current_term: { semester_id: '2026-2027-1', semester_name: '2026-2027-1' }, selected_semester: { semester_id: '2026-2027-1', semester_name: '2026-2027-1' }, semester_list: [{ semester_id: '2026-2027-1', semester_name: '2026-2027-1' }], grades: [] }),
      open_cloud_portal: () => result(null), open_calendar_guide: () => result(null),
    } };
  });
  await desktop.goto(base + '/desktop/index.html');
  await desktop.getByText('校园安排，一处就绪。').waitFor();
  assert.equal(await desktop.getByRole('menuitem', { name: '设置', exact: true }).count(), 0);
  await desktop.getByRole('menuitem', { name: '控制台', exact: true }).waitFor();
  assert.equal(await desktop.locator('.sidebar-version').count(), 0);
  assert.equal(await desktop.getByText('把校园安排，带在身边。', { exact: true }).count(), 0);
  const centeredToggle = () => desktop.locator('.sidebar-toggle').evaluate(button => {
    const toggle = button.getBoundingClientRect(), sidebar = button.closest('.workspace-sidebar').getBoundingClientRect();
    return Math.abs(toggle.x + toggle.width / 2 - sidebar.x - sidebar.width / 2) < 1 && toggle.width >= 44 && toggle.height >= 44;
  });
  assert.equal(await centeredToggle(), true, 'expanded sidebar toggle is centered with a 44px target');
  await desktop.locator('.sidebar-toggle').click();
  await desktop.waitForFunction(() => document.querySelector('.workspace-sidebar').offsetWidth === 76);
  assert.equal(await centeredToggle(), true, 'collapsed sidebar toggle stays centered');
  await desktop.screenshot({ path: path.join(output, 'desktop-sidebar-collapsed.png'), fullPage: true });
  await desktop.locator('.sidebar-toggle').click();
  await desktop.waitForFunction(() => document.querySelector('.workspace-sidebar').offsetWidth === 224);
  await desktop.screenshot({ path: path.join(output, 'desktop-console.png'), fullPage: true });
  await desktop.getByRole('button', { name: '管理本机账号' }).click();
  await desktop.getByText('切换本机账号', { exact: true }).waitFor();
  await desktop.keyboard.press('Escape');
  await desktop.getByRole('menuitem', { name: '日历导出' }).click();
  await desktop.getByText('2026-08-31', { exact: true }).waitFor();
  const slotToggle = desktop.getByRole('button', { name: '本校课时设置（一般无需修改）' });
  assert.equal(await slotToggle.getAttribute('aria-expanded'), 'false');
  assert.equal(await desktop.getByRole('textbox', { name: '第1-2节开始时间' }).isVisible(), false);
  await desktop.getByRole('button', { name: '导出 ICS 文件' }).click();
  await desktop.getByText('TEST_DOWNLOAD/classpush.ics').waitFor();
  assert.deepEqual(await desktop.evaluate(() => window.__savedCalendarConfig.time_slots), { '1-2': ['08:30', '10:05'], '3-4': ['10:25', '12:00'] });
  await desktop.screenshot({ path: path.join(output, 'desktop-calendar.png'), fullPage: true });
  await slotToggle.click();
  await desktop.getByRole('textbox', { name: '第1-2节开始时间' }).fill('08:35');
  await desktop.screenshot({ path: path.join(output, 'desktop-calendar-expanded.png'), fullPage: true });
  await slotToggle.click();
  await desktop.getByRole('button', { name: '导出 ICS 文件' }).click();
  await desktop.waitForFunction(() => window.__savedCalendarConfig.time_slots['1-2'][0] === '08:35');
  await desktop.getByRole('menuitem', { name: '关于 ClassPush' }).click();
  await desktop.getByText('湖南工学院的课表、成绩与日历学习空间。', { exact: false }).waitFor();
  assert.equal(await desktop.getByText('工作空间', { exact: false }).count(), 0);
  await desktop.getByRole('menuitem', { name: '课表预览' }).click();
  await desktop.getByText('测试课程（合成数据）', { exact: true }).first().waitFor();
  await desktop.getByRole('menuitem', { name: '云端推送' }).click();
  await desktop.getByRole('button', { name: '打开官网云端管理' }).waitFor();
  const site = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  site.on('pageerror', error => errors.push(error.message));
  await site.goto(base + '/index.html');
  await site.getByText('v3.0.1 · 正式发布 · 云端提醒与日历导出').waitFor();
  await site.screenshot({ path: path.join(output, 'website-home.png'), fullPage: true });
  await site.goto(base + '/download.html');
  await site.getByRole('link', { name: '下载桌面版 v3.0.1' }).waitFor();
  assert.equal(await site.locator('#desktop-download').getAttribute('href'), 'https://classpush.eliauk312.top/downloads/ClassPush_Setup_3.0.1.exe');
  assert.equal(await site.locator('.changelog-list li').count(), 5);
  for (const url of ['index.html', 'cloud.html', 'calendar.html', 'download.html', 'faq.html', 'privacy.html']) {
    await site.goto(base + '/' + url);
    assert.equal(await site.locator('.nav-links a').count(), 6);
    await site.locator('.site-footer').getByRole('link', { name: '云端推送管理', exact: true }).waitFor();
    assert.equal(await site.locator('a[href="#"]').count(), 0);
  }
  await site.goto(base + '/cloud.html');
  await site.screenshot({ path: path.join(output, 'cloud-login-desktop.png'), fullPage: true });
  await site.setViewportSize({ width: 375, height: 812 });
  await site.emulateMedia({ reducedMotion: 'reduce' });
  await site.getByRole('button', { name: '打开导航', exact: true }).click();
  assert.equal(await site.getByRole('button', { name: '关闭导航', exact: true }).getAttribute('aria-expanded'), 'true');
  await site.locator('.nav-links').getByRole('link', { name: '首页', exact: true }).click();
  await site.getByText('校园安排，带在身边', { exact: true }).waitFor();
  if (await site.evaluate(() => document.documentElement.scrollWidth > innerWidth)) console.log(await site.evaluate(() => [...document.querySelectorAll('body *')].map(element => ({ tag: element.tagName, class: element.className, right: element.getBoundingClientRect().right })).filter(element => element.right > innerWidth + 1).slice(0, 12)));
  assert.equal(await site.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile website overflow');
  await desktop.setViewportSize({ width: 375, height: 812 });
  await desktop.locator('.workspace-header').getByRole('button', { name: '展开导航', exact: true }).click();
  await desktop.getByRole('menuitem', { name: '控制台', exact: true }).click();
  await desktop.getByText('校园安排，一处就绪。').waitFor();
  await desktop.screenshot({ path: path.join(output, 'desktop-console-mobile.png'), fullPage: true });
  assert.equal(await desktop.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'mobile desktop overflow');
  assert.deepEqual(errors, []);
  await browser.close();
  console.log('UI smoke passed: mobile binding/settings/deletion, console/account/calendar/course/cloud, shared six-page navigation, mobile menu, no dead links or old receiving-channel copy. Synthetic data only.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(async () => { await activeBrowser?.close(); server.close(); });
