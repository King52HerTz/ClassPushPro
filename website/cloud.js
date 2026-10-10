'use strict';
const $ = id => document.getElementById(id);
let challenge = '';
let busy = false;
function feedback(message, type = '') {
  $('feedback').textContent = message;
  $('feedback').className = type;
  $('feedback').hidden = false;
  $('feedback').focus({ preventScroll: false });
}
async function request(path, method = 'GET', body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch('/api/cloud' + path, {
      method, credentials: 'same-origin', signal: controller.signal,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) showLogin();
      throw new Error(data.message || '云端服务暂未就绪，请稍后重试');
    }
    return data;
  } finally { clearTimeout(timer); }
}
async function action(fn) {
  if (busy) return;
  busy = true;
  document.querySelectorAll('button').forEach(button => button.disabled = true);
  $('feedback').hidden = true;
  try { await fn(); }
  catch (error) { feedback(error.name === 'AbortError' ? '等待超时，请刷新状态确认结果，不要连续重复提交。' : error.message || '网络异常，请重试', 'error'); }
  finally { busy = false; document.querySelectorAll('button').forEach(button => button.disabled = false); }
}
function showLogin() { $('loading').hidden = true; $('account-panel').hidden = true; $('login-panel').hidden = false; $('code-form').hidden = true; $('login-form').hidden = false; challenge = ''; }
async function loadAccount() {
  const account = await request('/account');
  $('loading').hidden = true; $('login-panel').hidden = true; $('account-panel').hidden = false;
  $('account-owner').textContent = `学号 ${account.username} · WxPusher ${account.uid}`;
  for (const key of ['morning', 'evening', 'grades', 'paused']) $(key).checked = account[key];
  $('account-state').textContent = account.needs_auth ? '需要处理授权 / 订阅' : account.paused ? '已暂停' : account.morning || account.evening || account.grades ? '已开启' : '尚未开启时段';
  $('account-notice').hidden = !account.notice;
  $('account-notice').textContent = account.notice;
  $('jobs').replaceChildren();
  const kinds = { morning: '晨间课表', evening: '晚间课表', grades: '成绩检查' };
  const states = { done: '已完成', failed: '未完成', unknown: '结果待确认', needs_auth: '需要登录', needs_binding: '需要重新订阅', skipped: '未发送', running: '处理中' };
  for (const job of account.jobs) {
    const li = document.createElement('li'), heading = document.createElement('strong'), message = document.createElement('p'), date = document.createElement('small');
    heading.textContent = `${kinds[job.kind] || '任务'} · ${states[job.status] || job.status}`;
    message.textContent = job.message;
    date.textContent = new Date(job.created * 1000).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) + '（北京时间）';
    li.append(heading, message, date); $('jobs').append(li);
  }
  if (!account.jobs.length) { const li = document.createElement('li'); li.textContent = '还没有任务记录。开启时段后，从下一批次开始执行。'; $('jobs').append(li); }
}
$('login-form').addEventListener('submit', event => { event.preventDefault(); action(async () => {
  const data = await request('/auth/request', 'POST', { username: $('username').value.trim(), password: $('password').value, uid: $('uid').value.trim(), consent: $('consent').checked });
  challenge = data.challenge; $('password').value = ''; $('login-form').hidden = true; $('code-form').hidden = false;
  feedback(data.message, 'success'); $('code').focus();
}); });
$('code-form').addEventListener('submit', event => { event.preventDefault(); action(async () => {
  await request('/auth/confirm', 'POST', { challenge, code: $('code').value.trim() });
  $('code').value = ''; challenge = ''; await loadAccount(); feedback('登录成功。请选择时段并保存；首次默认不开启推送。', 'success');
}); });
$('back').addEventListener('click', () => { challenge = ''; $('code').value = ''; $('code-form').hidden = true; $('login-form').hidden = false; });
$('settings-form').addEventListener('submit', event => { event.preventDefault(); action(async () => {
  const body = Object.fromEntries(['morning', 'evening', 'grades', 'paused'].map(key => [key, $(key).checked]));
  const data = await request('/account', 'PATCH', body); await loadAccount(); feedback(data.message, 'success');
}); });
$('test').addEventListener('click', () => action(async () => { const data = await request('/account/test', 'POST', {}); await loadAccount(); feedback(data.message, 'success'); }));
$('refresh').addEventListener('click', () => action(loadAccount));
$('logout').addEventListener('click', () => action(async () => {
  const data = await request('/auth/logout', 'POST', {}); showLogin(); $('code-form').hidden = true; $('login-form').hidden = false; feedback(data.message, 'success');
}));
$('password-form').addEventListener('submit', event => { event.preventDefault(); action(async () => {
  const data = await request('/account/password', 'POST', { password: $('new-password').value }); $('new-password').value = ''; await loadAccount(); feedback(data.message, 'success');
}); });
$('delete').addEventListener('click', () => {
  if (!confirm('确认关闭所有云端提醒并删除在线凭据、缓存和任务记录？需要重新绑定才能恢复。')) return;
  action(async () => { const data = await request('/account', 'DELETE', { confirm: 'DELETE' }); showLogin(); $('code-form').hidden = true; $('login-form').hidden = false; feedback(data.message, 'success'); });
});
loadAccount().catch(error => {
  showLogin();
  if (error.message !== '请先登录云端管理') feedback(error.message || '无法连接云端服务', 'error');
});
