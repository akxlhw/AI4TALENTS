@echo off
echo ============================================
echo AI4TALENT - Full Pipeline (migrate + seed)
echo ============================================
echo.

cd /d "%~dp0"

echo [1/2] Running database migration...
call "%~dp0migrate.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Migration failed. Aborting.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/2] Seeding database...
call "%~dp0seed.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Seed failed.
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================
echo Pipeline complete!
echo ============================================
echo.
pause
