'use strict';
(() => {
  const viewport = document.querySelector('.demo-viewport');
  if (viewport) {
    const resize = () => {
      const narrow = viewport.clientWidth < 600;
      const scale = narrow ? 1 : viewport.clientWidth / 1200;
      const frame = viewport.querySelector('iframe');
      frame.style.width = narrow ? '100%' : '1200px';
      frame.style.height = narrow ? '680px' : '850px';
      viewport.style.setProperty('--demo-scale', scale);
      viewport.style.height = (narrow ? 680 : Math.ceil(850 * scale)) + 'px';
    };
    new ResizeObserver(resize).observe(viewport);
    resize();
  }
  const content = document.getElementById('phone-demo-content');
  if (!content) return;
  const messages = {
    schedule: {
      title: '小主，明天有 3 节课，记得按时上课哟 🍬', stamp: '09-06 20:00',
      body: `<div class="wx-date">📅 09月07日 星期一 · 第2周</div>${[
        ['软件工程', '2611（多媒体）', '08:30–10:05（第1–2节）', '张老师（演示）'],
        ['体育4', '体育馆羽毛球场', '10:25–12:00（第3–4节）', '李老师（演示）'],
        ['毛泽东思想和中国特色社会主义理论体系概论', '数603（多媒体）', '14:00–15:35（第5–6节）', '何老师（演示）'],
      ].map(([name, place, time, teacher]) => `<section class="wx-course-item"><div class="wx-line title">📖 <strong>${name}</strong></div><div class="wx-line location">📍 ${place}</div><div class="wx-line time">⏰ ${time}</div><div class="wx-line teacher">👨‍🏫 ${teacher}</div></section>`).join('')}`,
    },
    empty: {
      title: '小主，明天全天没课，好好休息吧 🛌', stamp: '09-05 20:00',
      body: '<div class="wx-empty-day"><div class="wx-date">🗓️ 09月06日 星期日</div><div class="wx-empty-balloon" aria-hidden="true">🎈</div><p>自由时光，做点喜欢的事吧~</p><strong>祝你有美好的一天 ✨</strong></div>',
    },
    grades: {
      title: '小主，有新的成绩动态 🎉', stamp: '09-07 12:30',
      body: '<div class="wx-date">🎓 2026-2027-1 · 成绩变化</div><section class="wx-course-item"><div class="wx-line title">📖 <strong>软件工程</strong></div><div class="wx-line location">新增成绩 · 92 分</div><div class="wx-line teacher">3.0 学分 · 必修 · 演示成绩</div></section><p class="pusher-message-source">只在成绩变化时通知，不重复发送历史成绩。</p>',
    },
  };
  const appendMessage = (kind, received = false) => {
    const message = messages[kind];
    const entry = document.createElement('div');
    entry.className = 'pusher-message-entry';
    entry.innerHTML = `<div class="pusher-timestamp">${received ? '刚刚 · 演示接收' : message.stamp}</div><article class="wxpusher-card"><header class="wx-header"><h3 class="wx-title">${message.title}</h3><div class="wx-meta">ClassPush <time>${message.stamp}</time></div></header><div class="wx-body">${message.body}<p class="pusher-message-source">演示数据 · 请以教务最新安排为准</p></div></article>`;
    content.append(entry);
    while (content.children.length > 4) content.firstElementChild.remove();
    return entry;
  };
  const showMessage = entry => {
    content.scrollTop = entry.offsetTop;
  };
  appendMessage('empty');
  const initial = appendMessage('schedule');
  requestAnimationFrame(() => showMessage(initial));
  const receipt = document.getElementById('phone-receipt');
  let dismiss;
  document.querySelector('.phone-send-demo').addEventListener('click', () => {
    const kind = document.getElementById('phone-message-kind').value;
    const entry = appendMessage(kind, true);
    showMessage(entry);
    clearTimeout(dismiss);
    const notice = document.createElement('button');
    notice.type = 'button';
    notice.className = 'pusher-incoming';
    notice.innerHTML = `<span class="pusher-notice-app">WxPusher <small>刚刚</small></span><strong>ClassPush</strong><span>${messages[kind].title}</span><small>点击查看 · 本地演示</small>`;
    notice.addEventListener('click', () => { clearTimeout(dismiss); receipt.replaceChildren(); showMessage(entry); content.focus({ preventScroll: true }); });
    receipt.replaceChildren(notice);
    dismiss = setTimeout(() => receipt.replaceChildren(), 5000);
  });
})();
