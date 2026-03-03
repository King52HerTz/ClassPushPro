@echo off
cd /d "%~dp0"
echo Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies.
    pause
    exit /b
)

echo Starting ClassPush Pro (Restored)...
cd src
python main.py
pause
