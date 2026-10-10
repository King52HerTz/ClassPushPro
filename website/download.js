'use strict';
async function loadDownload() {
  const response = await fetch('version.json', { cache: 'no-store' });
  if (!response.ok) throw new Error('版本信息暂时不可用，请刷新后重试。');
  const release = await response.json();
  const available = release.available !== false;
  document.getElementById('desktop-version').textContent = `v${release.version} · ${available ? '当前正式下载' : '验收候选，尚未发布'}`;
  document.getElementById('desktop-release-date').textContent = `版本日期：${release.release_date || '以安装包为准'}`;
  const button = document.getElementById('desktop-download');
  const note = document.getElementById('desktop-note');
  if (!available) {
    button.textContent = '新版安装包待验收'; button.setAttribute('aria-disabled', 'true');
    note.textContent = '新版桌面已进入验收，正式安装包尚未切换。云端管理现在可直接使用。';
  } else {
    const url = new URL(release.download_url, location.href);
    if (url.protocol !== 'https:' || url.hostname !== 'classpush.eliauk312.top' || !url.pathname.toLowerCase().endsWith('.exe')) throw new Error('正式下载地址待确认，请联系开发者。');
    button.href = url.href; button.removeAttribute('aria-disabled'); button.textContent = `下载桌面版 v${release.version}`;
    note.textContent = String(release.version).startsWith('3.') ? 'Windows 10 / 11 64位 · 中文向导 · 可选盘符、安装目录和桌面快捷方式。升级前请退出旧软件。' : `当前下载为 v${release.version} 历史正式版，功能以对应版本为准。`;
  }
}
async function loadChanges() {
  const response = await fetch('site-info.json', { cache: 'no-store' });
  if (!response.ok) return;
  const info = await response.json();
  const list = document.getElementById('site-changelog');
  for (const change of info.changelog || []) { const item = document.createElement('li'); item.textContent = change; list.append(item); }
}
loadDownload().catch(error => { document.getElementById('desktop-note').textContent = error.message; });
loadChanges().catch(() => { document.getElementById('site-changelog').textContent = '更新说明暂时不可用，请稍后刷新。'; });
