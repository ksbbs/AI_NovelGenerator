@echo off
chcp 65001 >nul
REM AI小说生成器 - Windows启动脚本

echo ========================================
echo    AI小说生成器 Web 服务启动脚本
echo ========================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

REM 检查配置文件
if not exist "config.json" (
    echo [提示] 配置文件不存在，创建默认配置...
    python -c "from config_manager import create_config; create_config('config.json')"
)

REM 创建必要目录
if not exist "novels" mkdir novels
if not exist "vectorstore" mkdir vectorstore

REM 设置环境变量
if "%APP_USERNAME%"=="" set APP_USERNAME=admin
if "%APP_PASSWORD%"=="" set APP_PASSWORD=novel2024
set TZ=Asia/Shanghai

echo 启动参数:
echo   用户名: %APP_USERNAME%
echo   密码: %APP_PASSWORD%
echo   时区: %TZ%
echo ========================================
echo 服务即将启动，访问地址: http://localhost:7860
echo ========================================

REM 启动服务
python web_app.py

pause
