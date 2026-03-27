#!/bin/bash
# AI小说生成器 - 启动脚本
# 用于启动 Web 服务

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   AI小说生成器 Web 服务启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo -e "${YELLOW}配置文件不存在，创建默认配置...${NC}"
    python -c "from config_manager import create_config; create_config('config.json')"
fi

# 创建必要目录
mkdir -p novels vectorstore

# 设置环境变量
export APP_USERNAME=${APP_USERNAME:-admin}
export APP_PASSWORD=${APP_PASSWORD:-novel2024}
export TZ=${TZ:-Asia/Shanghai}

echo -e "${GREEN}启动参数:${NC}"
echo -e "  用户名: ${YELLOW}${APP_USERNAME}${NC}"
echo -e "  密码: ${YELLOW}${APP_PASSWORD}${NC}"
echo -e "  时区: ${YELLOW}${TZ}${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}服务即将启动，访问地址: http://localhost:7860${NC}"
echo -e "${GREEN}========================================${NC}"

# 启动服务
exec python web_app.py
