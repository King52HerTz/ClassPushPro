@echo off
setlocal
cd /d "%~dp0"

echo [0/4] Preparing environment...
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

if not exist "%~dp0setup.iss" (
    echo setup.iss not found
    exit /b 1
)

echo.
echo [1/4] Syncing installer version...
call :sync_setup_version
if %errorlevel% neq 0 (
    echo Sync setup.iss version failed
    exit /b 1
)

echo.
echo [2/4] Building frontend...
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
echo [3/4] Building executable...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
python -m PyInstaller --clean ClassPush.spec
if %errorlevel% neq 0 (
    echo PyInstaller failed
    exit /b 1
)

if exist dist\ClassPush\config.json del dist\ClassPush\config.json

echo.
echo [4/4] Build finished!
echo.
echo EXE output: %~dp0dist\ClassPush\ClassPush.exe
echo Installer script synced: %~dp0setup.iss
echo.
echo Next:
echo   1. Open %~dp0setup.iss
echo   2. Use Inno Setup Compiler to load it
echo   3. Click Compile to generate the installer
exit /b 0

:sync_setup_version
set "APP_VERSION="
if not exist "%~dp0RestoredSource\frontend\src\constants.ts" (
    echo constants.ts not found
    exit /b 1
)

for /f "tokens=2 delims='" %%i in ('findstr /c:"APP_VERSION" "%~dp0RestoredSource\frontend\src\constants.ts"') do (
    set "APP_VERSION=%%i"
)

if not defined APP_VERSION (
    echo Failed to read APP_VERSION from RestoredSource\frontend\src\constants.ts
    exit /b 1
)

powershell -NoProfile -Command "(Get-Content '%~dp0setup.iss') -replace '^#define MyAppVersion \".*\"$', '#define MyAppVersion \"%APP_VERSION%\"' | Set-Content '%~dp0setup.iss' -Encoding Default"
if %errorlevel% neq 0 (
    echo Failed to update setup.iss version
    exit /b 1
)

echo setup.iss version synced to %APP_VERSION%
exit /b 0
