@echo off
echo ============================================
echo AI4TALENT - Seed Database
echo ============================================
echo.

cd /d "%~dp0backend"

echo Initializing system data...
call .venv\Scripts\python.exe scripts/data/init_system.py --force

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Seed failed!
    pause
    exit /b %errorlevel%
)

echo.
echo Seed complete.
echo.
pause
