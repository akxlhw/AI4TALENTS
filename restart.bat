@echo off
chcp 65001 >nul
echo ============================================
echo 智能人才库 - 重启前后端服务
echo ============================================
echo.

echo [1/5] 停止现有服务...
taskkill /F /FI "WINDOWTITLE eq *Talent*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *npm*" 2>nul
timeout /t 2 /nobreak >nul

echo [2/5] 清理 Python 缓存...
cd /d %~dp0backend
del /s /q *.pyc 2>nul
for /d /r %%i in (__pycache__) do @rmdir /s /q "%%i" 2>nul
echo   缓存已清理

echo [3/5] 启动后端服务 (端口 8003)...
start "Talent Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8003"
timeout /t 3 /nobreak >nul

echo [4/5] 启动前端服务 (端口 2012)...
start "Talent Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo 服务已启动:
echo   后端 API: http://localhost:8003
echo   前端页面: http://localhost:2012
echo ============================================
echo.
pause
