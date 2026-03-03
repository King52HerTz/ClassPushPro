@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting ClassPush Pro (Dev Mode)...

echo [1/3] Checking environment...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed or not in PATH.
    pause
    exit /b
)
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

echo [2/3] Starting Frontend (New Window)...
start "Frontend Dev Server" cmd /k "cd frontend && npm run dev"

echo Waiting for frontend to initialize...
timeout /t 5 >nul

echo [2.5/3] Installing/Checking Dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Warning: Failed to install python dependencies.
    pause
)

echo [3/3] Starting Backend...
cd src
python main.py

if %errorlevel% neq 0 (
    echo Backend exited with error code %errorlevel%.
    pause
)
