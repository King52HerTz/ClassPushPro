// Visual interaction checks against the loopback-only preview. Synthetic data only.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('../private/qa-tools/node_modules/playwright');
const output = path.resolve(__dirname, '../private/qa-output');
const base = 'http://127.0.0.1:5175';

async function main() {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/index.html');
    await page.locator('.usage-ways').scrollIntoViewIfNeeded();
    const buttons = await page.locator('.usage-ways .btn').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().top));
    assert.equal(buttons.length, 3);
    assert.ok(Math.max(...buttons) - Math.min(...buttons) <= 1, 'three card buttons must align');
    await page.locator('.usage-ways').screenshot({ path: path.join(output, 'aligned-usage-cards.png') });
    await page.locator('#simulation-anchor').scrollIntoViewIfNeeded();
    const demo = page.frameLocator('.demo-viewport iframe');
    await demo.getByText('校园安排，一处就绪。').waitFor();
    await demo.getByRole('menuitem', { name: '课表预览', exact: true }).click();
    await demo.getByText('演示 · 计算机网络', { exact: true }).first().waitFor();
    await demo.getByRole('menuitem', { name: '日历导出', exact: true }).click();
    await demo.getByText('2026-08-31', { exact: true }).waitFor();
    await demo.getByRole('menuitem', { name: '控制台', exact: true }).click();
    assert.equal(await page.locator('.phone-view-tabs').count(), 0, 'phone must show received messages, not a timetable app');
    assert.equal(await page.locator('.pusher-message-entry').count(), 2, 'initial message history');
    await page.locator('.pusher-message-entry').last().getByText('📅 09月07日 星期一 · 第2周', { exact: true }).waitFor();
    const course = page.locator('.pusher-message-entry').last().locator('.wx-course-item').first();
    assert.equal(await course.evaluate(node => getComputedStyle(node).borderLeftColor), 'rgb(255, 107, 107)', 'preserve original red card accent');
    assert.equal(await course.locator('.location').evaluate(node => getComputedStyle(node).color), 'rgb(9, 132, 227)', 'preserve original blue location');
    assert.equal(await course.locator('.time').evaluate(node => getComputedStyle(node).color), 'rgb(225, 112, 85)', 'preserve original orange time');
    const receive = async (kind, title) => {
      await page.locator('#phone-message-kind').selectOption(kind);
      await page.getByRole('button', { name: '模拟收到一条消息', exact: true }).click();
      const banner = page.locator('#phone-receipt button');
      await banner.getByText('WxPusher', { exact: false }).waitFor();
      await banner.getByText(title, { exact: true }).waitFor();
      if (kind === 'schedule') {
        await page.locator('.showcase-phone').evaluate(node => node.scrollIntoView({ block: 'center', behavior: 'instant' }));
        await page.waitForTimeout(300); // Capture the completed incoming-banner transition.
        await page.locator('.showcase-phone').screenshot({ path: path.join(output, 'wxpusher-incoming-notification.png') });
      }
      await banner.click();
      assert.equal(await page.locator('#phone-receipt button').count(), 0, 'tap notification opens message');
      await page.locator('.pusher-message-entry').last().getByRole('heading', { name: title, exact: true }).waitFor();
      assert.ok(await page.locator('#phone-demo-content').evaluate(node => node.scrollTop > 0), 'show newest message in scrollable history');
    };
    await receive('grades', '小主，有新的成绩动态 🎉');
    await page.locator('.pusher-message-entry').last().getByText('新增成绩 · 92 分', { exact: true }).waitFor();
    await receive('empty', '小主，明天全天没课，好好休息吧 🛌');
    await receive('schedule', '小主，明天有 3 节课，记得按时上课哟 🍬');
    await page.locator('.pusher-message-entry').last().getByText('👨‍🏫 张老师（演示）', { exact: true }).waitFor();
    assert.equal(await page.locator('.pusher-message-entry').count(), 4, 'history stays bounded after replay');
    await page.locator('.showcase-phone').screenshot({ path: path.join(output, 'wxpusher-received-message.png') });
    await page.locator('#simulation-anchor').screenshot({ path: path.join(output, 'interactive-showcase.png') });

    await page.goto(base + '/desktop/index.html');
    assert.equal(await page.getByText('工作空间', { exact: false }).count(), 0);
    await page.getByText('学习空间', { exact: true }).waitFor();
    await page.getByRole('button', { name: '打开开发者彩蛋' }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByText('一只野生开发者。').waitFor();
    const lit = () => page.locator('.egg-fireworks').evaluate(canvas => canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data.some((value, index) => index % 4 === 3 && value > 0));
    await page.waitForFunction(() => {
      const canvas = document.querySelector('.egg-fireworks');
      return canvas && canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data.some((v, i) => i % 4 === 3 && v > 0);
    });
    await dialog.screenshot({ path: path.join(output, 'developer-easter-egg.png') });
    await page.evaluate(() => { window.__opened = []; window.open = url => { window.__opened.push(url); return null; }; });
    await dialog.getByRole('button', { name: '去博客串个门' }).click();
    await dialog.getByRole('button', { name: '去 GitHub 点亮 Star' }).click();
    const opened = await page.evaluate(() => window.__opened);
    assert.deepEqual(opened, ['https://eliauk312.top/', 'https://github.com/King52HerTz/ClassPushPro']);
    await page.waitForTimeout(2800);
    assert.equal(await lit(), false, 'fireworks must stop and clear');
    await page.keyboard.press('Escape');
    await dialog.waitFor({ state: 'hidden' });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('button', { name: '打开开发者彩蛋' }).click();
    await dialog.waitFor();
    assert.equal(await lit(), false, 'reduced motion must skip fireworks');
    await page.keyboard.press('Escape');

    for (const size of [{ width: 375, height: 812 }, { width: 812, height: 375 }]) {
      await page.setViewportSize(size);
      await page.goto(base + '/index.html');
      await page.locator('#simulation-anchor').scrollIntoViewIfNeeded();
      await demo.getByText('校园安排，一处就绪。').waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'website overflow');
      assert.equal(await demo.locator('html').evaluate(node => node.scrollWidth <= innerWidth), true, 'embedded desktop overflow');
      await receive('grades', '小主，有新的成绩动态 🎉');
      await page.locator('#phone-demo-content').focus();
      await page.keyboard.press('Home');
      await page.waitForFunction(() => document.getElementById('phone-demo-content').scrollTop === 0);
      assert.equal(await page.locator('#phone-demo-content').evaluate(node => node.scrollTop), 0, 'keyboard can browse message history');
      if (size.width === 375) await page.locator('#simulation-anchor').screenshot({ path: path.join(output, 'showcase-mobile.png') });
    }
    assert.deepEqual(errors, []);
    console.log('PASS: aligned card buttons, shared desktop showcase, WxPusher receipt/banner/details/history, learning space, egg links/fireworks/escape/reduced motion, portrait/landscape overflow.');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
