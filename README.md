# ClassPush · 湖南工学院

本地查课、手机日历、云端App 提醒。云端管理已开放，3.0.0 桌面版仍为验收候选，完成真实学校及 App 通知端到端验收后再正式发布。

[官网](https://classpush.eliauk312.top) · [云端管理](https://classpush.eliauk312.top/cloud.html) · [下载中心](https://classpush.eliauk312.top/download.html)

## 三个独立入口

- 桌面查询：保留本校课表、成绩查询；登录只需学号和教务密码，不用 UID。
- 日历导出：独立页面，导出本周、未来7天或全学期 ICS，支持提醒和课时设置。
- 云端推送：在官网绑定自己的教务账号和WxPusher UID，电脑关机也能运行；桌面入口打开同一个管理页。

本仓库仅维护湖南工学院版本，不包含其他学校的凭据、课时或缓存。

## 云端推送

北京时间两个独立时段：07:00 当天课表、20:00 次日课表。按队列发送，可能略有延迟。新开启或恢复从下一批次生效，不补发已过窗口的旧提醒。

成绩变化提醒在07:15–22:15每小时检查。首次开启和新学期首次检查只建立基线，不发送已有历史成绩。

首次绑定需同意服务器托管，并通过教务登录及WxPusher App 一次性验证码确认。已有账号无需重新填写 UID；验证码只发到原绑定接收人。可以暂停全部通知、更新教务密码、测试通知、查看最近任务或删除在线资料。退出管理不等于关闭推送。

AppToken 是本校应用的服务器凭据，用户不需要填写。UID 是每个人自己的App 收件地址，两者不同。学校或 WxPusher 服务异常、订阅失效和教务密码变化均可能影响投递，不保证永久免登录。

## 日历的边界

ICS 是导出时的快照，调课后不会自动同步。建议先导出本周测试，建立独立的 ClassPush 日历，重新导入前删除旧日历以免重复。未知学期日期不会猜测导出。

图文教程等待开发者提供真实手机操作图片后补充；当前仅提供入口和基本说明。

## 从2.x升级

新版停止创建和执行电脑本地定时推送，首次启动尝试停用本校旧任务。迁移失败会弹出明确提示。旧单人 GitHub Actions 推送及其 runner 已删除，保留测试 CI。

本机账号不会静默上传服务器，必须主动进行云端绑定。旧缓存缺少账号归属时不会作为离线数据使用，升级后请联网重新加载一次课表和成绩。退出本机账号不影响云端，关闭云端需进入官网管理。

Windows 安装包仍使用中文 Inno Setup，安装时可选择位置；官网与软件内更新继续使用项目服务器直链，不要求同学访问 GitHub 下载。

## 开发与验证

代码结构：

```text
RestoredSource/src/       本校教务客户端、桌面API和ICS生成
RestoredSource/frontend/  React + Ant Design桌面界面
cloud/                   Flask API、加密SQLite、单worker调度
website/                 自托管官网HTML/CSS/JS源码
deploy/                  systemd、Nginx和部署/回滚说明
docs/                    开发与验收文档
```

Python 3.10+，Node.js 20+。桌面运行需要Windows与WebView2。云端不安装pywebview，使用独立虚拟环境：

```bash
pip install -r cloud/requirements.txt
python -m unittest discover -s RestoredSource/tests -v
python -m unittest discover -s cloud/tests -v
python -m compileall -q RestoredSource/src cloud deploy
cd RestoredSource/frontend
npm ci
npm run build
```

源码桌面运行默认加载构建产物；只有显式设置 `CLASSPUSH_DEV=1` 才连接本地开发服务器，避免误加载另一学校的测试界面。

[开发与验收方案](docs/云端版开发与验收.md) · [部署和回滚](deploy/README.md) · [使用说明](TUTORIAL.md) · [FAQ](FAQ.md)

自动化测试使用假教务和假推送，不能代替真实登录、App 收件和手机日历验证。后端健康检查、生产构建与真实业务成功分别记录。

## 安全

云端每账号的凭据、会话和课程/成绩缓存独立加密。主密钥与AppToken只存在服务器私有环境文件，不进入源码或桌面安装包。运营者掌握服务器和解密密钥，这不是端到端加密，托管前请阅读[隐私说明](https://classpush.eliauk312.top/privacy.html)。

不要将密码、AppToken、Cookie、验证码、配置文件或数据库提交到Git。测试反馈请使用脱敏日志。若发现凭据泄漏，请立即轮换。

通知和管理验证码通过 [WxPusher 独立 App](https://wxpusher.zjiecode.com/download/) 接收，请先安装并开启通知权限。官网导航、帮助与云端入口共用同一套界面；桌面账号操作在右上角。
