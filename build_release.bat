@echo off
setlocal
cd /d "%~dp0"

echo [0/3] Preparing environment...
echo WorkDir: %cd%

set "LOG=%~dp0build_release.log"
call :main > "%LOG%" 2>&1
set "CODE=%errorlevel%"

if %CODE% neq 0 (
    echo [ERROR] Build failed with code %CODE%
    echo See log: %LOG%
    type "%LOG%"
    pause
    exit /b %CODE%
)

echo [SUCCESS] Build finished!
echo See log: %LOG%
pause
exit /b 0

:main
if exist "%~dp0.venv\Scripts\activate.bat" call "%~dp0.venv\Scripts\activate.bat"

echo.
echo [1/3] Building frontend...
pushd RestoredSource\frontend
REM Clean cache
if exist dist rmdir /s /q dist
if exist node_modules\.vite rmdir /s /q node_modules\.vite
call npm run build
if %errorlevel% neq 0 (
    echo Frontend build failed
    exit /b 1
)
popd

echo.
echo [2/3] Building executable...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
python -m PyInstaller --clean ClassPush.spec
if %errorlevel% neq 0 (
    echo PyInstaller failed
    exit /b 1
)

if exist dist\ClassPush\config.json del dist\ClassPush\config.json

echo.
echo [3/3] Build finished!
exit /b 0
