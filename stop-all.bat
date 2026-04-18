@echo off
chcp 65001 >nul
echo ========================================
echo   停止所有 Node.js/Vite 开发服务器
echo ========================================
echo.

:: 停止 Vite 开发服务器 (node.exe 进程)
echo [1/3] 正在查找并停止 Node.js 进程...
taskkill /F /IM node.exe 2>nul
if %errorlevel% equ 0 (
     echo   ✓ 已停止所有 Node.js 进程
 ) else (
     echo   ℹ 未找到运行中的 Node.js 进程
 )
echo.

:: 清理可能的端口占用 (3000, 5173 等常见开发端口)
echo [2/3] 检查端口占用情况...
for %%p in (3000 5173 5174 8080 8081) do (
     netstat -ano | findstr :%%p | findstr LISTENING >nul 2>&1
     if not errorlevel 1 (
         for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%p ^| findstr LISTENING') do (
             echo   ⚠ 端口 %%p 被 PID %%a 占用
         )
     )
 )
echo.

:: 清理 Vite 临时文件
echo [3/3] 清理 Vite 缓存...
if exist "web_frontend\node_modules\.vite" (
     rmdir /s /q "web_frontend\node_modules\.vite" 2>nul
     echo   ✓ 已清理 Vite 缓存
 ) else (
     echo   ℹ 无需清理缓存
 )
echo.

echo ========================================
echo   所有服务已停止
echo ========================================
pause
