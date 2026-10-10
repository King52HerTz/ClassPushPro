// Loopback-only visual preview. Never contacts production, school, or WxPusher APIs.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const repo = path.resolve(__dirname, '..');
const mime = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.ico': 'image/x-icon', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg' };
const bridge = fs.readFileSync(path.join(__dirname, 'preview_bridge.js'), 'utf8');
let account = { username: '20260001', uid: 'UID***DEMO', morning: true, evening: true, grades: false,
  paused: false, needs_auth: false, notice: '', jobs: [{ kind: 'evening', status: 'done',
    message: '演示记录：此预览没有发送真实通知。', created: Date.now() / 1000 }] };
const badge = `<aside style="position:fixed;bottom:10px;right:12px;z-index:99999;max-width:calc(100vw - 24px);padding:8px 12px;border:1px solid #bdd5ff;border-radius:10px;background:#f1f7ff;color:#234c88;font:12px/1.5 system-ui;box-shadow:0 3px 16px #0001"><a href="/__preview__/" style="color:inherit">本地演示预览 · 切换页面</a><br>不连接教务、不发送通知，请勿填真实密码</aside>`;
const sendJson = (res, status, data, headers = {}) => {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers });
  res.end(JSON.stringify(data));
};
const cookie = enabled => ({ 'Set-Cookie': `preview_account=${enabled ? '1' : '0'}; Path=/; SameSite=Strict` });
http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://127.0.0.1');
    const name = decodeURIComponent(url.pathname);
    if (name.startsWith('/api/cloud/')) {
      let raw = '';
      for await (const part of req) { raw += part; if (raw.length > 16384) { sendJson(res, 413, { message: '请求过大' }); return; } }
      const data = raw ? JSON.parse(raw) : {};
      const action = name.slice('/api/cloud'.length);
      const logged = /(?:^|;\s*)preview_account=1(?:;|$)/.test(req.headers.cookie || '');
      if (action === '/auth/request') return sendJson(res, 200, { challenge: 'LOCAL_DEMO', message: '演示验证码：123456。不会发送真实消息，也不保存输入的密码。' });
      if (action === '/auth/confirm') return sendJson(res, data.code === '123456' ? 200 : 400,
        { message: data.code === '123456' ? '演示登录成功' : '演示验证码为 123456' }, data.code === '123456' ? cookie(true) : {});
      if (action === '/auth/logout') return sendJson(res, 200, { message: '已退出演示账号' }, cookie(false));
      if (!logged) return sendJson(res, 401, { message: '请先登录云端管理' });
      if (action === '/account' && req.method === 'GET') return sendJson(res, 200, account);
      if (action === '/account' && req.method === 'PATCH') {
        for (const key of ['morning', 'evening', 'grades', 'paused']) if (typeof data[key] === 'boolean') account[key] = data[key];
      }
      if (action === '/account' && req.method === 'DELETE') return sendJson(res, 200, { message: '已退出演示；没有真实账号被删除' }, cookie(false));
      return sendJson(res, 200, { message: '演示操作成功，没有保存真实凭据或发送通知。' });
    }
    if (name === '/__preview__/') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ClassPush 调试预览</title><body style="margin:60px auto;padding:24px;max-width:760px;font:16px/1.8 system-ui;background:#f5f8ff;color:#182230"><h1>ClassPush 界面调试预览</h1><p>仅预览湖南工学院版。这些页面全部使用演示数据，不连接真实教务、不发送通知，请勿输入真实密码。</p><ul><li><a href="/desktop/index.html">桌面控制台</a>：可切换课表、成绩、日历和云端入口</li><li><a href="/index.html">官网首页</a>：共享导航、下载中心、帮助页面</li><li><a href="/cloud.html?preview=login">云端登录页面</a>：演示验证码 123456</li><li><a href="/cloud.html?preview=account">云端已绑定页面</a>：时段开关、任务记录、账号管理</li></ul><p>本次不生成新安装包，也不发布到线上。</p></body></html>`);
    }
    const desktop = name.startsWith('/desktop/');
    const root = path.join(repo, desktop ? 'RestoredSource/frontend/dist' : 'website');
    const relative = desktop ? name.slice('/desktop'.length) : name === '/' ? '/index.html' : name;
    const file = path.resolve(root, '.' + relative);
    const resolved = path.relative(root, file);
    if (resolved.startsWith('..') || path.isAbsolute(resolved) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      res.writeHead(404); return res.end('Not found');
    }
    const headers = { 'Content-Type': (mime[path.extname(file)] || 'application/octet-stream') + '; charset=utf-8', 'Cache-Control': 'no-store' };
    if (name === '/cloud.html' && url.searchParams.has('preview')) Object.assign(headers, cookie(url.searchParams.get('preview') === 'account'));
    res.writeHead(200, headers);
    if (path.extname(file) === '.html') {
      let html = fs.readFileSync(file, 'utf8');
      if (desktop) html = html.replace('<head>', '<head><script>' + bridge + '</script>');
      return res.end(html.replace('</body>', badge + '</body>'));
    }
    fs.createReadStream(file).pipe(res);
  } catch { if (!res.headersSent) sendJson(res, 400, { message: '预览请求无效' }); else res.end(); }
}).listen(5175, '127.0.0.1', () => process.stdout.write('Local visual preview: http://127.0.0.1:5175/__preview__/\n'));
