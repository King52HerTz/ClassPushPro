@echo off
setlocal

cd /d "%~dp0"

set "LOG=%~dp0build_release.log"
call :main > "%LOG%" 2>&1
set "CODE=%errorlevel%"

type "%LOG%"
echo.
echo ExitCode: %CODE%
echo LogFile: %LOG%
echo.
pause
exit /b %CODE%

:main
echo [0/3] Preparing environment...
echo WorkDir: %cd%

if exist "%~dp0.venv\Scripts\activate.bat" goto has_venv
echo WARNING: Virtual environment not found (.venv)
echo You may be using system Python.
goto after_venv
:has_venv
echo Activating virtual environment...
call "%~dp0.venv\Scripts\activate.bat"
:after_venv

echo Python:
where python
python --version

echo NPM:
where npm
call npm --version

REM Check PyInstaller
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo WARNING: PyInstaller not found. Installing...
    pip install pyinstaller pywin32
) else (
    REM Ensure pywin32 is installed for win32com support
    pip install pywin32
)

echo.
echo [1/3] Building frontend...
if not exist RestoredSource\frontend\package.json goto no_frontend
pushd RestoredSource\frontend
call npm run build
if %errorlevel% neq 0 goto frontend_failed
popd
goto after_frontend
:no_frontend
echo ERROR: Frontend folder not found: RestoredSource\frontend
exit /b 1
:frontend_failed
echo ERROR: Frontend build failed
popd
exit /b 1
:after_frontend

echo.
echo [2/3] Building executable with PyInstaller...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

if not exist ClassPush.spec goto no_spec

python -m PyInstaller --clean ClassPush.spec
if %errorlevel% neq 0 goto pyinstaller_failed

if exist dist\ClassPush\config.json del dist\ClassPush\config.json

if not exist dist\ClassPush\ClassPush.exe goto no_exe

echo.
echo [3/3] Build finished! Please open setup.iss in Inno Setup manually.
echo Next steps:
echo 1. Open "setup.iss" with Inno Setup Compiler.
echo 2. Click "Compile" button (or press F9).
exit /b 0

:no_spec
echo ERROR: ClassPush.spec not found in %cd%
exit /b 1

:pyinstaller_failed
echo ERROR: PyInstaller build failed
exit /b 1

:no_exe
echo ERROR: Output executable not found: dist\ClassPush\ClassPush.exe
exit /b 1
