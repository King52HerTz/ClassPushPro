# ClassPush

湖南工学院课表与成绩推送工具。桌面端负责查看课表、成绩和导出日历；云端版使用 GitHub Actions，即使电脑关机也能按时把消息发到 WxPusher。

![Hnit](https://img.shields.io/badge/Hnit-强智教务系统-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![License](https://img.shields.io/badge/License-MIT-green)

## 现在能做什么

- 自动登录湖南工学院强智教务系统并获取课表。
- 根据 `isNowWeek` 区分正常教学周和假期，不会再把暑假当成“第2周”。
- 开学后根据教务当前周次自动校准第1周周一，不需要每学期修改代码。
- 早上推送今天课表，晚上推送明天课表。
- 查看不同学期的成绩，检测新增成绩和成绩修改。
- 将成绩变化整理成适合手机阅读的 HTML 卡片并推送。
- 导出 ICS 日历，支持自定义节次时间和提醒时间。
- 教务系统暂时不可用时使用最近一次有效缓存；超过最后教学周后旧缓存会自动失效。

假期里看不到“下学期课表”是正常现象——学校还没发布的数据，程序也不能从空气里抓出来 qwq。等教务系统切换学期并发布课表后，刷新即可自动更新。

## 两种使用方式

### Windows 桌面版

1. 在 [Releases](https://github.com/King52HerTz/ClassPushPro/releases) 下载 `ClassPush_Setup.exe`。
2. 登录教务系统并填写 WxPusher UID。
3. 根据需要开启课表推送、成绩推送和开机自启。

桌面端配置保存在当前 Windows 用户目录下的 `.ClassPush` 文件夹。设置页里的“第1周周一”现在只是人工兜底，通常留空即可。

### GitHub Actions 云端版

1. Fork 本仓库。
2. 打开仓库 `Settings → Secrets and variables → Actions`。
3. 新建以下 Repository secrets：

| Secret | 说明 |
| --- | --- |
| `CP_USERNAME` | 教务系统学号 |
| `CP_PASSWORD` | 教务系统密码 |
| `CP_APP_TOKEN` | WxPusher 应用 AppToken |
| `CP_UID` | 接收消息的 WxPusher UID |
| `CP_CONFIG_JSON_B64` | 可选，本地配置的 Base64，用于首次建立缓存 |

4. 打开 Actions，启用需要的工作流。

当前工作流：

- `Morning Push (07:00)`：北京时间07:00推送当天课表。
- `Night Push (20:00)`：北京时间20:00推送第二天课表。
- `Grade Check (Hourly)`：北京时间07:17～23:17每小时检查一次成绩。

成绩工作流第一次运行只建立成绩基线，不会把历史成绩全部轰到手机上。之后只有新增成绩或成绩被修改时才推送。

> 不要把 `config.json`、学号、密码或 AppToken 提交到仓库。`config.json` 即使经过当前程序处理，也不适合放在公开 Git 历史中。可选缓存请按照 [云端部署教程](TUTORIAL.md) 转成 Base64 后存入 GitHub Secret。

## 关于 AppToken

官方桌面版继续兼容现有 WxPusher 应用和已有用户，本次升级不会轮换 AppToken，也不会要求已有用户重新关注。

如果你 Fork 后给自己或同学单独部署，建议创建自己的 WxPusher 应用，并把 AppToken 放进 GitHub Secret。AppToken 是发送权限，不要贴在 Issue、截图、日志或聊天记录中。

## 开发

项目结构：

```text
RestoredSource/
├─ src/          Python 后端、教务适配和推送任务
├─ frontend/     React + TypeScript 桌面界面
└─ tests/        Python 单元测试
.github/workflows/  云端课表、成绩和 CI 工作流
```

环境要求：

- Python 3.12
- Node.js 20+
- Windows 桌面打包需要 PyWebView、PyInstaller 和 Inno Setup

后端：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r RestoredSource/requirements.txt
python RestoredSource/src/main.py
```

前端：

```powershell
cd RestoredSource/frontend
npm ci
npm run dev
```

运行检查：

```powershell
python -m unittest discover -s RestoredSource/tests -v
cd RestoredSource/frontend
npm run build
```

## 数据与使用说明

- 桌面版的教务账号保存在本机；云端版会把账号放在你自己仓库的 GitHub Secrets 中。
- 云端任务会访问教务系统、GitHub Actions 和 WxPusher，因此不能表述为“绝不上传任何第三方服务”。请根据自己的接受程度选择桌面版或云端版。
- 程序只读取当前用户可正常访问的课表和成绩，不提供绕过认证、批量扫描或破坏教务系统的功能。
- 请控制检查频率。默认成绩检查为每小时一次，不建议改成几分钟一次。
- 教务系统字段或登录流程调整后，适配器可能需要更新，欢迎提交 Issue 或 Pull Request。

## License

[MIT License](LICENSE)
