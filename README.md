# ClassPush 🎓

> 教务系统可以慢，早八不能迟到。

ClassPush 是一个给湖南工学院同学用的课表与成绩推送工具。它能查看课表、查成绩、导出日历，还能通过 WxPusher 把提醒送到手机上。

电脑经常关机？可以用 GitHub Actions 云端版。教务系统偶尔发癫？现在会自动补试。至于假期为什么没有下学期课表——学校还没发的数据，程序确实不能从空气里抓出来 qwq。

![Hnit](https://img.shields.io/badge/Hnit-强智教务系统-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![License](https://img.shields.io/badge/License-MIT-green)

## 它现在会干什么

- 自动登录教务系统并获取课表。
- 自动判断当前是教学周、假期，还是“学校还没把新课表端上来”。
- 开学后根据教务系统返回的周次校准第 1 周，不用每学期手改日期。
- 早上推今天的课，晚上推明天的课。
- 教务系统或 GitHub Actions 临时卡住时自动补试，成功后不重复推送。
- 查看不同学期成绩；有新成绩或老师修改成绩时再提醒。
- 推送内容使用适合手机阅读的 HTML 卡片，不是一大坨朴实无华的纯文字。
- 导出 ICS 日历，可以自己调整节次时间和提前提醒时间。
- 在线抓取失败时尝试最近一次有效缓存，旧学期缓存过期后不会继续硬撑。

## 怎么用

这里有两条路线，按自己的电脑开机积极程度选择。

### Windows 桌面版

适合想直接点点鼠标、顺便在电脑上看课表和成绩的同学。

1. 到 [Releases](https://github.com/King52HerTz/ClassPushPro/releases) 下载最新版 `ClassPush_Setup.exe`。
2. 安装并登录教务系统。
3. 填写 WxPusher UID，根据需要开启课表推送、成绩推送和开机自启。

配置保存在当前 Windows 用户目录的 `.ClassPush` 文件夹中。设置页里的“第 1 周周一”只是人工兜底，一般留空就行，让程序自己算。

### GitHub Actions 云端版 ☁️

适合电脑一关机就进入贤者模式，但手机提醒还得继续上班的情况。

1. Fork 本仓库。
2. 打开自己仓库的 `Settings → Secrets and variables → Actions`。
3. 新建下面这些 Repository secrets：

| Secret | 填什么 |
| --- | --- |
| `CP_USERNAME` | 教务系统学号 |
| `CP_PASSWORD` | 教务系统密码 |
| `CP_APP_TOKEN` | WxPusher 应用 AppToken |
| `CP_UID` | 接收消息的 WxPusher UID |
| `CP_CONFIG_JSON_B64` | 可选，本地配置的 Base64，用于首次带上缓存 |

4. 打开 `Actions`，启用需要的工作流。

不会配置也别慌，照着 [云端部署教程](TUTORIAL.md) 一步一步点就行。代码不会因为你盯着它看而跑得更快，但教程真的能让它跑起来。

## 云端版什么时候推送

课表工作流现在不会只押宝一次：

- `Morning Push`：北京时间 `07:00`、`07:20`、`07:40` 检查，推送今天课表。
- `Night Push`：北京时间 `20:00`、`20:20`、`20:40` 检查，推送明天课表。
- `Grade Check`：北京时间 `07:17～23:17` 每小时检查一次成绩。

这里的三个课表时间不是“三连发”。每次成功后，程序会记录类似 `morning:2026-09-07` 的场次键；后面的补发任务看到它就会直接下班。只有前一次没成功，下一次才会继续尝试。

GitHub Actions 的定时任务偶尔会晚几分钟启动，这是平台调度的正常现象，不是你的表突然穿越了。

成绩工作流第一次运行只建立基线，不会把大学以来的成绩一次性轰到手机上。之后有新增或修改才推送——没消息有时也是好消息，当然也可能是老师还没录。

## AppToken 别乱贴

官方桌面版会继续兼容现有 WxPusher 应用和已有用户，升级不会要求大家重新关注。

如果你 Fork 后自己部署，建议创建自己的 WxPusher 应用，把 AppToken 放进 GitHub Secret。AppToken 相当于应用的发消息钥匙，不要放进代码、Issue、截图或聊天记录里。钥匙贴在门上，再结实的锁也很难发挥实力。

同样不要把 `config.json`、学号或密码提交到仓库。需要给云端带缓存时，请按教程转换成 Base64 后放入 Secret；Base64 是搬运格式，不是隐身术。

## 常见问题

### 暑假为什么显示不了下学期课表？

因为教务系统还没发布。等学校切换学期并放出课表后，刷新就会自动获取。这个时候疯狂点击刷新，只能锻炼食指。

### 为什么设置里还有“第 1 周周一”？

它现在是兜底选项。正常情况下程序会根据教务系统的当前周次自动校准；只有学校字段再次整活时，才需要人工救场。

### 补发会不会触发 WxPusher 风控？

成功后的补发任务不会再次调用 WxPusher，只会快速检查本地状态然后退出。真正失败时一天最多尝试三个课表时间，比每几分钟轮询温和得多。

### Windows 为什么提示“未知发布者”？

目前安装包还没有购买代码签名证书。请只从本仓库 Releases 下载，并对照 Release 中提供的 SHA-256 校验值。

## 想改代码的话

项目大致长这样：

```text
RestoredSource/
├─ src/          Python 后端、教务适配和推送任务
├─ frontend/     React + TypeScript 桌面界面
└─ tests/        Python 单元测试
.github/workflows/  云端课表、成绩和 CI 工作流
```

需要 Python 3.12、Node.js 20+。Windows 打包另外需要 PyWebView、PyInstaller 和 Inno Setup。

```powershell
# 后端
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r RestoredSource/requirements.txt
python RestoredSource/src/main.py

# 前端
cd RestoredSource/frontend
npm ci
npm run dev
```

提交前可以跑一下：

```powershell
python -m unittest discover -s RestoredSource/tests -v
cd RestoredSource/frontend
npm run build
```

如果它在你电脑上能跑、换台电脑就不跑，恭喜，你遇到了软件开发中非常经典的“在我这里是好的”。欢迎带上日志提交 Issue。

## 数据与使用说明

- 桌面版教务账号保存在本机；云端版账号保存在你自己仓库的 GitHub Secrets 中。
- 云端任务会访问教务系统、GitHub Actions 和 WxPusher，请按自己的接受程度选择使用方式。
- 程序只读取当前账号正常可访问的课表和成绩，不提供绕过认证、批量扫描或破坏教务系统的功能。
- 请保持合理检查频率。成绩默认每小时检查一次，不建议改成五分钟催一次，老师不会因此录得更快。
- 教务系统字段或登录流程变化后可能需要重新适配，欢迎提交 Issue 或 Pull Request。

## License

[MIT License](LICENSE) —— 可以学习、修改和分享，记得保留原作者与许可证信息。
