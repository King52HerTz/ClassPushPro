// Render the actual cloud send callback with synthetic account/cache data only.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('../private/qa-tools/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const source = `
import json, tempfile
from datetime import datetime
from cloud.service import SchoolService, BEIJING
from cloud.store import Store
now = datetime(2026, 10, 11, 20, tzinfo=BEIJING).timestamp()
with tempfile.TemporaryDirectory() as directory:
    service = SchoolService(Store(directory, b'K' * 32), clock=lambda: now)
    state = {'username': '20260001', 'course_cache': {
        'username': '20260001', 'semester_id': '2026-2027-1', 'fetched_at': now - 3600,
        'teaching': {'semester_id': '2026-2027-1', 'schedule_status': 'active',
                     'week_one_monday': '2026-08-31', 'available_weeks': [7]},
        'courses': [dict(courseName=name, location='演示教室', teacherName='演示老师',
                         classTime=period, startNode=node, xqmc='星期一', classWeekDetails='7')
                    for name, period, node in [('合成测试课程一', '5-6', 5),
                                               ('合成测试课程二（较长课程名称换行测试）', '7-8', 7)]]}}
    results = []
    for kind in ['morning', 'evening']:
        service.run({'state': state}, kind, datetime(2026, 10, 12).date(),
                    lambda content, title: results.append(dict(content=content, title=title)))
    print(json.dumps(results, ensure_ascii=False))
`;
async function main() {
  const messages = JSON.parse(execFileSync(path.join(root, '.venv/Scripts/python.exe'), ['-c', source],
    { cwd: root, encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } }));
  const output = path.join(root, 'private/qa-output');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
  try {
    const page = await browser.newPage();
    const requests = [];
    page.on('request', request => requests.push(request.url()));
    for (const width of [375, 940]) {
      await page.setViewportSize({ width, height: 1100 });
      for (const [index, message] of messages.entries()) {
        assert.ok(message.title.includes(index ? '明天' : '今天'));
        await page.setContent('<meta name="viewport" content="width=device-width,initial-scale=1">' + message.content);
        const text = await page.locator('body').innerText();
        for (const value of ['14:00-15:35', '15:55-17:30', '演示教室', '演示老师', '课表数据时间']) assert.ok(text.includes(value));
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        assert.equal(await page.locator('div').evaluateAll(nodes => nodes.filter(n => getComputedStyle(n).borderLeftColor === 'rgb(255, 120, 117)' && getComputedStyle(n).borderLeftWidth === '5px').length), 2);
        await page.screenshot({ path: path.join(output, `actual-cloud-payload-${width}-${index ? 'evening' : 'morning'}.png`), fullPage: true });
      }
    }
    assert.deepEqual(requests, []);
  } finally { await browser.close(); }
  console.log('PASS: actual cloud callback uses original copy/colors/times on mobile/desktop; synthetic data only, no network or messages.');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
