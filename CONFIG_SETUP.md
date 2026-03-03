# 项目配置与安全指南 (Configuration Setup)

## ⚠️ 安全警告

本项目代码库中**不应包含任何真实的敏感信息**（如密码、Token、UID等）。所有敏感配置应通过环境变量或本地配置文件进行管理。

## 1. 配置文件 (Config File)

项目使用 `config.json` 存储运行时配置。

### 1.1 创建配置文件
复制模板文件 `config.example.json` 并重命名为 `config.json`：

```bash
cp config.example.json config.json
```

### 1.2 填写配置项
打开 `config.json` 并填入您的真实信息：

| 字段名 | 必填 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `openid` | ✅ | WxPusher 用户 UID | `UID_xxxxxx` |
| `username` | ✅ | 教务系统账号 | `20210001` |
| `password` | ✅ | 教务系统密码 | `mypassword` |
| `wx_app_token` | ✅ | WxPusher 应用 Token | `AT_xxxxxx` |
| `push_time` | ❌ | 每日推送时间 | `20:00` |

> **注意**：`config.json` 已被加入 `.gitignore`，请勿将其提交到版本控制系统。

## 2. 环境变量 (Environment Variables)

对于生产环境或不想使用文件配置的场景，支持以下环境变量：

- `WX_APP_TOKEN`: WxPusher 应用 Token (优先级高于配置文件)

## 3. 敏感信息获取渠道

### 3.1 WxPusher UID & Token
1. 访问 [WxPusher 后台](https://wxpusher.zjiecode.com/admin/)。
2. 创建一个新的应用，获取 `APP_TOKEN`。
3. 关注应用后，在“用户列表”或手机推送中查看您的 `UID`。

## 4. 开发环境设置

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. 运行前端：
   ```bash
   cd frontend
   npm run dev
   ```

3. 运行后端：
   ```bash
   python src/main.py
   ```

## 5. 生产环境部署

- 推荐使用 `pyinstaller` 打包为可执行文件。
- 打包后，配置文件将默认存储在用户的“文档”目录 (`Documents/ClassPush/config.json`)。
- 请确保目标机器的时间准确，以免影响定时任务。

## 6. 清理与验证

在提交代码前，请运行以下命令检查是否有敏感信息残留：

```bash
grep -r "UID_" .
grep -r "AT_" .
```
