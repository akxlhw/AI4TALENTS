@echo off
echo ============================================
echo AI4TALENT - Restart Services
echo ============================================
echo.

echo [1/5] Stopping existing services...
taskkill /F /FI "WINDOWTITLE eq *Talent*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *npm*" 2>nul
timeout /t 2 /nobreak >nul

echo [2/5] Cleaning Python cache...
cd /d %~dp0backend
del /s /q *.pyc 2>nul
for /d /r %%i in (__pycache__) do @rmdir /s /q "%%i" 2>nul
echo   Cache cleaned

echo [3/5] Starting backend (port 8003)...
start "Talent Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8003"
timeout /t 3 /nobreak >nul

echo [4/5] Starting frontend (port 2012)...
start "Talent Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo Services started:
echo   Backend API: http://localhost:8003
echo   Frontend: http://localhost:2012
echo   LAN Access: http://YOUR_IP:2012
echo ============================================
echo.
pause
