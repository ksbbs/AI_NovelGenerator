# api/routes.py
# -*- coding: utf-8 -*-
"""
FastAPI 路由处理器
"""
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import os
import logging
from pydantic import ValidationError

from .schemas import (
    GenerateArchitectureRequest, GenerateBlueprintRequest, GenerateChapterDraftRequest,
    FinalizeChapterRequest, ConsistencyCheckRequest, ImportKnowledgeRequest,
    BuildPromptRequest, EnrichChapterRequest, SaveConfigRequest, BatchGenerateRequest,
    TaskStatus, MessageResponse, FileContentResponse, ChapterListResponse, RoleLibraryResponse
)
from .services import get_service

router = APIRouter()
templates = Jinja2Templates(directory="api/templates")

# ============== HTTP 页面路由 ==============

@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """配置页面"""
    service = get_service()
    config = service.load_config()
    return templates.TemplateResponse("config.html", {
        "request": request,
        "config": config
    })


@router.get("/setting/{filepath:path}", response_class=HTMLResponse)
async def setting_page(request: Request, filepath: str):
    """小说设定页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    content = service.get_file_content(filepath, "Novel_architecture.txt")
    return templates.TemplateResponse("setting.html", {
        "request": request,
        "filepath": filepath,
        "content": content or ""
    })


@router.get("/directory/{filepath:path}", response_class=HTMLResponse)
async def directory_page(request: Request, filepath: str):
    """章节目录页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    content = service.get_file_content(filepath, "Novel_directory.txt")
    return templates.TemplateResponse("directory.html", {
        "request": request,
        "filepath": filepath,
        "content": content or ""
    })


@router.get("/character/{filepath:path}", response_class=HTMLResponse)
async def character_page(request: Request, filepath: str):
    """角色状态页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    content = service.get_file_content(filepath, "character_state.txt")
    return templates.TemplateResponse("character.html", {
        "request": request,
        "filepath": filepath,
        "content": content or ""
    })


@router.get("/summary/{filepath:path}", response_class=HTMLResponse)
async def summary_page(request: Request, filepath: str):
    """全局摘要页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    content = service.get_file_content(filepath, "global_summary.txt")
    return templates.TemplateResponse("summary.html", {
        "request": request,
        "filepath": filepath,
        "content": content or ""
    })


@router.get("/chapters/{filepath:path}", response_class=HTMLResponse)
async def chapters_page(request: Request, filepath: str):
    """章节列表页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    chapters = service.list_chapters(filepath)
    return templates.TemplateResponse("chapters.html", {
        "request": request,
        "filepath": filepath,
        "chapters": chapters
    })


@router.get("/chapter/{filepath:path}/{chapter_num:int}", response_class=HTMLResponse)
async def chapter_page(request: Request, filepath: str, chapter_num: int):
    """单章内容页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    content = service.get_file_content(os.path.join(filepath, "chapters"), f"chapter_{chapter_num}.txt")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "filepath": filepath,
        "chapter_num": chapter_num,
        "content": content or ""
    })


@router.get("/role_library/{filepath:path}", response_class=HTMLResponse)
async def role_library_page(request: Request, filepath: str):
    """角色库页面"""
    filepath = filepath.lstrip('/')
    service = get_service()
    roles = service.list_role_library(filepath)
    return templates.TemplateResponse("role_library.html", {
        "request": request,
        "filepath": filepath,
        "roles": roles
    })


# ============== API 路由 - 配置管理 ==============

@router.get("/api/config")
async def get_config():
    """获取完整配置"""
    service = get_service()
    config = service.load_config()
    return config


@router.post("/api/config/save")
async def save_config(request: Dict[str, Any]):
    """保存配置"""
    service = get_service()
    config = service.load_config()
    # 更新传入的配置项
    for key, value in request.items():
        if key in config:
            config[key] = value
    success = service.save_config(config)
    return {"status": "success" if success else "failed", "message": "配置已保存" if success else "配置保存失败"}


@router.post("/api/config/llm")
async def save_llm_config(request: Dict[str, Any]):
    """保存LLM配置"""
    service = get_service()
    config = service.load_config()
    if "llm_configs" not in config:
        config["llm_configs"] = {}
    name = request.get("name", "")
    if name:
        config["llm_configs"][name] = {
            "interface_format": request.get("interface_format", "OpenAI"),
            "api_key": request.get("api_key", ""),
            "base_url": request.get("base_url", ""),
            "model_name": request.get("model_name", ""),
            "temperature": request.get("temperature", 0.7),
            "max_tokens": request.get("max_tokens", 8192),
            "timeout": request.get("timeout", 600)
        }
        service.save_config(config)
        return {"status": "success", "message": f"LLM配置 '{name}' 已保存"}
    return {"status": "error", "message": "配置名称不能为空"}


@router.delete("/api/config/llm/{name}")
async def delete_llm_config(name: str):
    """删除LLM配置"""
    service = get_service()
    config = service.load_config()
    if "llm_configs" in config and name in config["llm_configs"]:
        del config["llm_configs"][name]
        service.save_config(config)
        return {"status": "success", "message": f"LLM配置 '{name}' 已删除"}
    return {"status": "error", "message": f"LLM配置 '{name}' 不存在"}


@router.post("/api/config/embedding")
async def save_embedding_config(request: Dict[str, Any]):
    """保存Embedding配置"""
    service = get_service()
    config = service.load_config()
    if "embedding_configs" not in config:
        config["embedding_configs"] = {}
    name = request.get("name", "")
    if name:
        config["embedding_configs"][name] = {
            "interface_format": request.get("interface_format", "OpenAI"),
            "api_key": request.get("api_key", ""),
            "base_url": request.get("base_url", ""),
            "model_name": request.get("model_name", ""),
            "retrieval_k": request.get("retrieval_k", 4)
        }
        service.save_config(config)
        return {"status": "success", "message": f"Embedding配置 '{name}' 已保存"}
    return {"status": "error", "message": "配置名称不能为空"}


@router.delete("/api/config/embedding/{name}")
async def delete_embedding_config(name: str):
    """删除Embedding配置"""
    service = get_service()
    config = service.load_config()
    if "embedding_configs" in config and name in config["embedding_configs"]:
        del config["embedding_configs"][name]
        service.save_config(config)
        return {"status": "success", "message": f"Embedding配置 '{name}' 已删除"}
    return {"status": "error", "message": f"Embedding配置 '{name}' 不存在"}


@router.post("/api/config/choose")
async def save_choose_config(request: Dict[str, str]):
    """保存配置选择"""
    service = get_service()
    config = service.load_config()
    if "choose_configs" not in config:
        config["choose_configs"] = {}
    config["choose_configs"].update(request)
    service.save_config(config)
    return {"status": "success", "message": "配置选择已保存"}


# ============== API 路由 - 小说生成 ==============

@router.post("/api/generate/architecture")
async def api_generate_architecture(request: Dict[str, Any]):
    """生成小说架构"""
    service = get_service()
    task_id = await service.generate_architecture(request)
    return {"task_id": task_id, "status": "pending", "message": "架构生成任务已启动"}


@router.post("/api/generate/blueprint")
async def api_generate_blueprint(request: Dict[str, Any]):
    """生成章节目录"""
    service = get_service()
    task_id = await service.generate_blueprint(request)
    return {"task_id": task_id, "status": "pending", "message": "目录生成任务已启动"}


@router.post("/api/generate/chapter-draft")
async def api_generate_chapter_draft(request: Dict[str, Any]):
    """生成章节草稿"""
    service = get_service()
    task_id = await service.generate_chapter_draft(request)
    return {"task_id": task_id, "status": "pending", "message": "章节草稿生成任务已启动"}


@router.post("/api/generate/finalize")
async def api_finalize_chapter(request: Dict[str, Any]):
    """定稿章节"""
    service = get_service()
    task_id = await service.finalize_chapter(request)
    return {"task_id": task_id, "status": "pending", "message": "章节定稿任务已启动"}


@router.post("/api/generate/batch")
async def api_batch_generate(request: Dict[str, Any]):
    """批量生成章节"""
    service = get_service()
    task_id = await service.batch_generate(request)
    return {"task_id": task_id, "status": "pending", "message": "批量生成任务已启动"}


@router.post("/api/generate/build-prompt")
async def api_build_prompt(request: Dict[str, Any]):
    """构建章节提示词"""
    service = get_service()
    task_id = await service.build_prompt(request)
    # 由于这是同步的简单操作，我们立即返回结果
    # 但为了保持一致性，我们仍然使用任务系统
    return {"task_id": task_id, "status": "pending", "message": "提示词构建任务已启动"}


@router.post("/api/generate/enrich")
async def api_enrich_chapter(request: Dict[str, Any]):
    """扩写章节"""
    service = get_service()
    try:
        chapter_text = request.get("chapter_text", "")
        word_number = request.get("word_number", 3000)
        llm_config_name = request.get("llm_config_name", "final_chapter_llm")

        result = await service.enrich_chapter(chapter_text, word_number, llm_config_name)
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"扩写章节失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============== API 路由 - 一致性检查 ==============

@router.post("/api/check/consistency")
async def api_check_consistency(request: Dict[str, Any]):
    """一致性检查"""
    service = get_service()
    try:
        result = await service.check_consistency(
            request.get("filepath", ""),
            request.get("chapter_num", 1),
            request.get("llm_config_name", "consistency_review_llm")
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"一致性检查失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============== API 路由 - 文件操作 ==============

@router.get("/api/file/content")
async def api_get_file_content(filepath: str = "", filename: str = ""):
    """获取文件内容"""
    service = get_service()
    try:
        content = service.get_file_content(filepath, filename)
        return {"status": "success", "content": content, "exists": True}
    except:
        return {"status": "success", "content": "", "exists": False}


@router.post("/api/file/save")
async def api_save_file(request: Dict[str, Any]):
    """保存文件内容"""
    service = get_service()
    try:
        success = service.save_file_content(
            request.get("filepath", ""),
            request.get("filename", ""),
            request.get("content", "")
        )
        return {"status": "success" if success else "error", "message": "文件已保存" if success else "文件保存失败"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/file/chapters")
async def api_list_chapters(filepath: str = ""):
    """获取章节列表"""
    service = get_service()
    chapters = service.list_chapters(filepath)
    return {"status": "success", "chapters": chapters}


# ============== API 路由 - 知识库 ==============

@router.post("/api/knowledge/import")
async def api_import_knowledge(request: Dict[str, Any]):
    """导入知识库"""
    service = get_service()
    try:
        result = await service.import_knowledge(
            request.get("filepath", ""),
            request.get("content", ""),
            request.get("embedding_config_name", "OpenAI")
        )
        return {"status": "success", "message": "知识库导入成功"}
    except Exception as e:
        logging.error(f"知识库导入失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/api/knowledge/clear")
async def api_clear_vectorstore(request: Dict[str, Any]):
    """清空向量库"""
    service = get_service()
    try:
        result = await service.clear_vectorstore(request.get("filepath", ""))
        return {"status": "success", "message": "向量库已清空"}
    except Exception as e:
        logging.error(f"清空向量库失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============== API 路由 - 任务管理 ==============

@router.get("/api/task/{task_id}")
async def api_get_task_status(task_id: str):
    """获取任务状态"""
    service = get_service()
    task = service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task_id": task_id, **task}


@router.get("/api/tasks/running")
async def api_get_running_tasks():
    """获取所有运行中的任务"""
    service = get_service()
    tasks = service.get_all_running_tasks()
    return {"tasks": tasks}


# ============== API 路由 - 角色库 ==============

@router.get("/api/role-library")
async def api_list_role_library(filepath: str = ""):
    """列出角色库"""
    service = get_service()
    roles = service.list_role_library(filepath)
    return {"status": "success", "roles": roles}


@router.get("/api/role-library/content")
async def api_get_role_content(filepath: str = "", category: str = "", role_name: str = ""):
    """获取角色内容"""
    service = get_service()
    try:
        content = service.get_role_content(filepath, category, role_name)
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/api/role-library/save")
async def api_save_role_content(request: Dict[str, Any]):
    """保存角色内容"""
    service = get_service()
    try:
        success = service.save_role_content(
            request.get("filepath", ""),
            request.get("category", ""),
            request.get("role_name", ""),
            request.get("content", "")
        )
        return {"status": "success" if success else "error", "message": "角色已保存" if success else "角色保存失败"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/api/role-library/role")
async def api_delete_role(filepath: str = "", category: str = "", role_name: str = ""):
    """删除角色"""
    service = get_service()
    try:
        success = service.delete_role(filepath, category, role_name)
        return {"status": "success" if success else "error", "message": "角色已删除" if success else "角色删除失败"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/api/role-library/category")
async def api_create_category(request: Dict[str, Any]):
    """创建分类"""
    filepath = request.get("filepath", "")
    category = request.get("category", "")
    if not category:
        return {"status": "error", "message": "分类名称不能为空"}

    category_dir = os.path.join(filepath, "角色库", category)
    try:
        os.makedirs(category_dir, exist_ok=True)
        return {"status": "success", "message": f"分类 '{category}' 已创建"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
