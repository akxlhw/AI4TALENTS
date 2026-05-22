@echo off
echo ============================================
echo AI4TALENT - Database Migration
echo ============================================
echo.

cd /d "%~dp0backend"

echo Running migrations...
call .venv\Scripts\python.exe -m alembic upgrade head

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Migration failed!
    pause
    exit /b %errorlevel%
)

echo.
echo Migration complete.
echo.
pause
