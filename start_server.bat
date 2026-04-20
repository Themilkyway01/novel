@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ========================================
echo     网文小说推荐系统 - 启动脚本
echo ========================================
echo.

:: 设置 Redis 路径
set "REDIS_PATH=D:\Redis-x64-3.0.504"
set "REDIS_CONFIG=redis.windows.conf"

:: 检查 Redis 是否已安装
if not exist "%REDIS_PATH%\redis-server.exe" (
    echo ✗ 错误：找不到 Redis 服务器
    echo 请确保 Redis 已安装到：%REDIS_PATH%
    pause
    exit /b 1
)

:: 设置 Node.js 路径 (JetBrains 运行时)
set "NODE_PATH=C:\Users\TianHe\AppData\Local\JetBrains\acp-agents\.runtimes\node\24.13.0\bin"

:: 临时添加 npm 到 PATH
if exist "%NODE_PATH%\npm.cmd" (
    set "PATH=%NODE_PATH%;%PATH%"
    echo ✓ 已配置 Node.js 路径：%NODE_PATH%
) else (
    echo ✗ 错误：找不到 Node.js 路径
    pause
    exit /b 1
)

:: 检查 npm 是否可用（直接检测文件而非使用 where 命令）
if not exist "%NODE_PATH%\node.exe" (
    echo ⚠ 警告：node.exe 未找到，请检查 Node.js 路径配置
    pause
    exit /b 1
)
"%NODE_PATH%\node.exe" --version >nul
if %errorlevel% neq 0 (
    echo ⚠ 警告：Node.js 无法正常运行
    pause
    exit /b 1
)
echo ✓ Node.js 已就绪

:: 启动 Redis 服务
echo [1/3] 启动 Redis 缓存服务...
echo Redis 路径：%REDIS_PATH%

cd /d "%REDIS_PATH%"
start "Redis Server" cmd /c "redis-server.exe %REDIS_CONFIG%"
cd /d "%~dp0"
echo Redis 服务已启动 (端口 6379)
echo   等待 3 秒确保 Redis 初始化...
timeout /t 3 /nobreak >nul

:: 启动 Django 后端（绑定 0.0.0.0 以支持局域网访问）
echo [2/3] 启动 Django 后端...
cd web_backend
start "Django Backend" cmd /k "call venv\Scripts\activate && python manage.py runserver 0.0.0.0:8000"
cd ..
echo ✓ 后端已启动：http://localhost:8000/api

:: 启动 Vue 前端
echo [3/3] 启动 Vue 前端...
cd web_frontend
start "Vue Frontend" cmd /k "set PATH=%NODE_PATH%;%PATH% && npm run dev"
cd ..
echo ✓ 前端已启动：http://localhost:3000

echo.
echo ========================================
echo     系统启动完成！
echo.
echo     Redis 缓存: redis://127.0.0.1:6379/1
echo     访问地址：http://localhost:3000
echo     管理员：admin / admin123
echo ========================================
echo.
pause
