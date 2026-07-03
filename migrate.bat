@echo off
echo ============================================
echo AI4TALENT - Database Migration
echo ============================================
echo.

cd /d "%~dp0backend"

echo Checking for orphaned migration state (e.g. deprecated lw_* tables)...
call .venv\Scripts\python.exe scripts\fix\cleanup_orphaned_lab_web_tables.py --yes
rem Cleanup script is idempotent: no-ops on healthy databases, only acts if
rem the orphaned '051_add_lab_web_site' revision is detected.

echo.
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
