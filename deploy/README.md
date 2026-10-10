# 部署与回滚（仅湖南工学院）

生产网站仍是静态站，新增 API 反代，不覆盖其他网站。后端 Python 3.10+、虚拟环境、独立 classpush 系统用户、SQLite。HTTP 端口只监听 loopback，无需开放新的公网端口。SSH 端口以管理员配置为准，不提交主机凭据。

1. 备份原官网、Nginx 配置、现有安装包及 version.json；备份放在站点目录之外，禁止公开下载包含个人资料的备份。
2. 将 `cloud`、`RestoredSource/src`（仅源码，不含配置/日志）、`RestoredSource/requirements-core.txt` 放到 `/opt/classpush-cloud/releases/<release>/`，`current` 指向本次版本。
3. 在 `/opt/classpush-cloud/venv` 安装 `cloud/requirements.txt`。数据目录 `/var/lib/classpush-cloud` 归 classpush，权限700；程序目录只读。
4. `/etc/classpush-cloud.env` 保存实际密钥及本校 AppToken，权限600，绝不打印。`CLOUD_DATA_KEY` 为随机32字节base64。已有部署绝不重新生成密钥。AppToken 只从私有文件安全迁移，不复用其他学校 token、不迁移任何个人教务密码。
5. 安装两个 service，先完成 Linux 自动测试，再启动 API 与 worker。数据库本身加密，但主密钥与备份必须同时保护。运行日志仅记录固定安全错误，不输出 HTTP 凭据。
6. 把 `nginx-cloud.conf` 包含在现有 HTTPS server 内，保持原证书、下载路径和静态root。先 `nginx -t` 再 reload；失败恢复备份，不中断原官网。
   宝塔服务器使用实际运行的 `/www/server/nginx/sbin/nginx` 检查和 reload，不要误用系统的 `/usr/sbin/nginx`。回滚仅恢复本次改动的公开文件，避免覆盖宝塔保护的 `.user.ini`。
7. 发布官网时保留 `ClassPush_Setup.exe` 和用户已有其他下载文件。新 version.json 最后切换；验收前 `available=false`，不得把旧包宣传为3.0。正式发布时安装包SHA256、版本及大小同时更新。
   官网页面使用 `Cache-Control: no-store`，JS/CSS 要求重新验证；每次发布同步更新 `site.js` 的 `siteRelease` 和各页面的资源查询标识。不能只在无缓存的新浏览器验证，要运行 `node qa/navigation_cache_smoke.cjs` 检查已缓存旧首页、旧下载页的用户也能正常跳转。
8. 验证 `/api/cloud/health`、页面静态资源MIME、Cookie安全属性、未经授权返回401以及后端/worker进程。真实学校登录、微信收件及早晚任务需在用户授权的真实账号完成，不能用health替代。

## 回滚

`systemctl stop classpush-cloud-api classpush-cloud-worker`，恢复 Nginx 和官网备份并检查配置后 reload。恢复 `current` 链接和服务即可回滚代码；不要删除数据库或密钥。旧单人推送 timer 保持禁用，不能和新服务同时运行。保留备份供恢复，但含个人资料的备份最多保留30天，管理员需安排清理；项目默认不创建个人资料备份。

## 日常检查

检查两个 service、任务状态及 needs_auth/needs_binding 数量，不输出用户数据。worker 30秒扫描一次，按账号串行、批次截止45分钟、唯一键去重。日志出现未知投递不要盲目重发；查询 WxPusher 后台再决定。大量账号时应先评估批次吞吐再开放，不承诺当前单worker支持无限人数。
