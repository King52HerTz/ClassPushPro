# ClassPush - 湖工(Hnit)专属课程推送助手 🎓

> 一个专为 Hnit 学子打造的桌面端课程推送工具，基于 Python + React + PyWebView 开发，对接强智教务系统，让你的课表触手可及。

![ClassPush](https://img.shields.io/badge/Hnit-强智教务系统-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-0078D6) ![Status](https://img.shields.io/badge/Status-Active-success)

## 📖 项目简介

ClassPush 是一款轻量级的 Windows 桌面应用，旨在解决教务系统访问繁琐、容易忘记上课时间的问题。它能够自动登录湖南工学院（Hnit）的强智教务系统，抓取最新课表，并通过WxPusher app每天定时接收推送的次日的课程安排。

本项目不仅是一个实用的工具，也为对 **Python 爬虫**、**React 前端** 以及 **桌面应用开发** 感兴趣的同学提供了一个完整的参考案例。

---

## ✨ 核心功能

- ✅ **自动登录**：只需首次输入学号密码，后续自动完成教务系统认证。
- 📅 **智能课表**：精准解析强智教务系统数据，自动识别当前周次、单双周课程。
- 🔔 **微信推送**：每天定时（默认 20:00 或 07:00）推送课程提醒到WxPusher app，不再错过任何一节课。
- 🚀 **开机自启**：支持开机静默启动，在此期间自动检测并执行推送任务。
- 🛡️ **离线模式**：教务系统崩溃或网络不佳时，自动切换至本地缓存课表，保证查看无阻。
- 🔒 **隐私安全**：所有账号密码均采用 AES 加密存储在本地用户目录，绝不上传任何第三方服务器。

---

## 🛠️ 技术栈 (For Developers)

本项目采用前后端分离架构，通过 `pywebview` 将 Web 前端封装为本地桌面应用。

### 前端 (Frontend)
- **框架**: [React](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **UI 组件库**: [Ant Design (antd)](https://ant.design/)
- **构建工具**: [Vite](https://vitejs.dev/)
- **路由**: React Router

### 后端 (Backend)
- **语言**: Python 3.8+
- **GUI 容器**: [pywebview](https://pywebview.flowrl.com/) (轻量级浏览器内核)
- **爬虫**: Requests + BeautifulSoup / Selenium (针对强智教务系统适配)
- **加密**: PyCryptodome (AES 加密配置)
- **任务调度**: Windows Task Scheduler (通过 win32com 调用)

### 打包与部署
- **Python 打包**: [PyInstaller](https://pyinstaller.org/)
- **安装包制作**: [Inno Setup](https://jrsoftware.org/isinfo.php)

---

## 🚀 快速开始 

### 方案一：桌面版 (适合小白)

#### 1. 下载安装
从 [Releases](https://github.com/King52HerTz/ClassPushPro/releases) 页面下载最新的安装包 `ClassPush_Setup.exe` 并安装。

#### 2. 初始化配置
首次运行软件，点击 **"去设置"** 或 **"登录"**：
- **学号/密码**：输入你的 Hnit 教务系统账号密码。
- **UID**：这是用于WxPusher app推送的唯一标识。
    - 点击输入框旁的 **"如何获取 UID"**。
    - 扫描二维码关注 "WxPusher消息推送平台" 公众号。
    - 点击 "我的" -> "我的UID"，复制并填入软件。

#### 3. 开启自动推送
- 在设置页面开启 **"开机自启"**。
- 设置你喜欢的 **"推送时间"** (建议晚上 20:00 推送次日课表，或早上 07:00 推送今日课表)。
- 点击 **"保存配置"**。

🎉 **大功告成！** 软件将会在后台静默运行，你只需要留意WxPusher app消息即可。

---

### 方案二：GitHub Actions 云端版 (强烈推荐) ☁️

**无需下载软件，无需电脑开机，利用 GitHub 免费服务器每天自动推送！**

#### 1. Fork 本仓库
点击右上角的 **Fork** 按钮，将本项目复制到你自己的 GitHub 账号下。

#### 2. 配置账号密码 (Secrets)
进入你 Fork 后的仓库，依次点击：
`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

添加以下 4 个变量 (注意大小写)：

| Name | Value (示例) | 说明 |
| :--- | :--- | :--- |
| `CP_USERNAME` | `20210001` | 你的教务系统学号 |
| `CP_PASSWORD` | `123456` | 你的教务系统密码 |
| `CP_APP_TOKEN` | `AT_xxxx` | WxPusher AppToken (可填默认或自己的) |
| `CP_UID` | `UID_xxxx` | 你的 WxPusher UID |

#### 3. 启用自动运行
1. 点击仓库上方的 **Actions** 选项卡。
2. 点击绿色按钮 **I understand my workflows, go ahead and enable them**。
3. 左侧点击 **ClassPush Daily Run**，右侧点击 **Run workflow** 手动触发一次测试。
4. 如果手机收到推送，恭喜你！以后每天早上 07:00 (北京时间) 会自动推送。

---

## 💻 开发指南 

如果你想学习如何开发此类软件，或想为本项目贡献代码，请参考以下步骤：

### 环境准备
- Node.js 16+
- Python 3.8+ (建议使用虚拟环境)

### 1. 克隆项目
```bash
git clone https://github.com/King52HerTz/ClassPushPro.git
cd ClassPushPro
```

### 2. 后端设置
```bash
# 创建虚拟环境
python -m venv .venv
# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 安装依赖
pip install -r RestoredSource/requirements.txt
```

### 3. 前端设置
```bash
cd RestoredSource/frontend
npm install
```

### 4. 运行开发模式
**方式一 (推荐)**：
1. 在一个终端运行前端：
   ```bash
   cd RestoredSource/frontend
   npm run dev
   ```
2. 在另一个终端运行后端 (需激活虚拟环境)：
   ```bash
   # 回到项目根目录
   python RestoredSource/src/main.py
   ```
   *注意：`main.py` 会自动检测本地 5173 端口的开发服务器。*

### 5. 打包发布
本项目提供了一键构建脚本 `build_release.bat`，它会自动执行以下步骤：
1. 编译 React 前端代码 (`npm run build`)。
2. 使用 PyInstaller 打包 Python 后端为 EXE。
3. (可选) 提示使用 Inno Setup 编译生成最终安装包。

```bash
# 在项目根目录运行
.\build_release.bat
```

---

## ⚠️ 免责声明

1. 本项目仅供编程学习和技术交流使用，**严禁用于任何商业用途**。
2. 本项目通过模拟登录方式获取数据，**不包含任何破坏计算机信息系统**的功能。
3. 请妥善保管好自己的教务系统账号和密码，虽然软件已做加密处理，但使用者仍需对自己的账号安全负责。
4. 如有侵权，请联系作者删除。

---

## 📄 License

MIT License
