# api/main.py
# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import logging

# 配置日志
logging.basicConfig(
    filename='app.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI(
    title="AI Novel Generator",
    description="AI-based novel generation web application",
    version="2.0.0"
)

# 数据目录（Docker volume mount）
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="api/static"), name="static")

# 模 板引擎
templates = Jinja2Templates(directory="api/templates")

# 导入路由
from .routes import router
app.include_router(router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页 - Novel Generator Dashboard"""
    from .services import get_service
    service = get_service()
    config = service.load_config()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "config": config
    })

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "data_dir": DATA_DIR}

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    from .services import initialize_service
    initialize_service()
    logging.info("AI Novel Generator API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logging.info("AI Novel Generator API shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
