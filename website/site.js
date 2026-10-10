'use strict';
// One navigation and footer for the introduction site and cloud workspace.
const currentPage = location.pathname.split('/').pop() || 'index.html';
const pages = [['index.html', '首页'], ['cloud.html', '云端管理'], ['calendar.html', '日历说明'], ['download.html', '下载中心'], ['faq.html', '使用帮助']];
const siteRelease = '20261011-policy1';
const header = document.querySelector('[data-site-header]');
if (header) {
  header.innerHTML = `<a class="skip-link" href="#main-content">跳到主要内容</a><nav class="navbar" aria-label="网站导航"><div class="container nav-container"><a class="logo site-logo" href="index.html" aria-label="ClassPush 首页"><img src="favicon-96x96.png" alt=""><span><span class="text-blue">Class</span><span class="text-dark">Push</span></span></a><div class="nav-links" id="site-navigation">${pages.map(([url, label]) => `<a href="${url}" ${currentPage === url ? 'aria-current="page"' : ''}>${label}</a>`).join('')}<a class="btn btn-sm btn-primary" href="cloud.html">进入云端</a></div><button type="button" class="mobile-menu-btn" aria-label="打开导航" aria-controls="site-navigation" aria-expanded="false"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button></div></nav>`;
  const toggle = header.querySelector('button');
  const links = header.querySelector('.nav-links');
  const close = () => { links.classList.remove('active'); toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-label', '打开导航'); };
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') !== 'true';
    links.classList.toggle('active', expanded); toggle.setAttribute('aria-expanded', String(expanded)); toggle.setAttribute('aria-label', expanded ? '关闭导航' : '打开导航');
  });
  links.addEventListener('click', close);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { close(); toggle.focus(); } });
}
const footer = document.querySelector('[data-site-footer]');
if (footer) footer.innerHTML = `<div class="container"><div class="site-footer-grid"><div><a class="footer-brand" href="index.html"><span class="text-blue">Class</span><span class="text-dark">Push</span></a><p>校园安排，带在身边。<br>仅面向湖南工学院，免费与开源。</p></div><div><h2>开始使用</h2><a href="cloud.html">云端推送管理</a><a href="calendar.html">日历导出说明</a><a href="download.html">桌面版下载与更新</a></div><div><h2>帮助与支持</h2><a href="faq.html">常见问题</a><a href="privacy.html">托管与隐私说明</a><a href="mailto:shdx2024@qq.com">联系开发者</a></div><div><h2>关于项目</h2><a href="https://github.com/King52HerTz/ClassPushPro" target="_blank" rel="noopener noreferrer">GitHub 源码</a><a href="https://wxpusher.zjiecode.com/download/" target="_blank" rel="noopener noreferrer">下载 WxPusher App</a><span>QQ 交流群：1084681551</span></div></div><div class="site-footer-bottom"><span>© 2026 ClassPush · Eliauk</span><a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">湘ICP备2026003086号-2</a></div></div>`;

// Old HTML may still be fresh in a visitor's browser, even after server headers change.
for (const link of document.querySelectorAll('a[href]')) {
  const url = new URL(link.getAttribute('href'), location.href);
  if (url.origin === location.origin && /^\/(index|cloud|calendar|download|faq|privacy)\.html$/.test(url.pathname)) {
    url.searchParams.set('v', siteRelease);
    link.setAttribute('href', url.pathname + url.search + url.hash);
  }
}
