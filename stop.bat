@echo off
chcp 65001 >nul
echo ============================================
echo 智能人才库 - 停止所有服务
echo ============================================
echo.

echo 正在停止后端服务...
taskkill /F /FI "WINDOWTITLE eq *Talent Backend*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *uvicorn*" 2>nul

echo 正在停止前端服务...
taskkill /F /FI "WINDOWTITLE eq *Talent Frontend*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *npm*" 2>nul

echo.
echo 所有服务已停止。
pause
