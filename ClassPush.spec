# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 定义前端资源路径
frontend_dist = 'RestoredSource/frontend/dist'
frontend_public = 'RestoredSource/frontend/public'

a = Analysis(
    ['RestoredSource/src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含前端构建产物 (整个dist文件夹)
        (frontend_dist, 'frontend/dist'),
        # 包含图标文件 (放在根目录)
        (os.path.join(frontend_public, 'icon.ico'), '.'),
        # 包含源代码 (用于运行时动态加载部分逻辑)
        # 排除 action_runner.py (它是云端专用入口，不需要打包到桌面版)
        # PyInstaller 本身会递归分析 imports，不需要手动把 src 放进去作为 data
        # 如果确实需要把 py 文件当资源放进去，应该过滤掉 action_runner.py
        # 但其实这里把 src 当 data 放进去是不推荐的做法，除非你有动态加载 py 文件的需求
        # 为了保险起见，我们保留原有逻辑，但加上说明
        ('RestoredSource/src', 'src'),
    ],
    excludes=[
        # 显式排除云端运行器，防止被意外打包进去 (虽然打包进去也没害处，只是占空间)
        # 'action_runner', 
    ],
    hiddenimports=[
        'win32timezone',
        'engineio.async_drivers.threading',
        'flask_socketio',
        'clr_loader',
        'pythonnet',
        'webview.platforms.edgechromium',
        'pystray',
        'PIL.Image',
        'win10toast',
        'requests',
        'bs4',
        'Crypto',
        'win32com.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # excludes=[],  <-- 这一行是重复的，需要删除
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClassPush',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # 关闭控制台窗口 (GUI模式)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(frontend_public, 'icon.ico'),
    uac_admin=False, # 不需要强制管理员权限 (解决部分电脑白屏问题)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClassPush',
)
