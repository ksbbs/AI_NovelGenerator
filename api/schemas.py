# api/schemas.py
# -*- coding: utf-8 -*-
"""
Pydantic 模型用于请求和响应验证
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ============== 配置相关模型 ==============

class LLMConfig(BaseModel):
    """LLM 配置模型"""
    name: str
    interface_format: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 8192
    timeout: int = 600


class EmbeddingConfig(BaseModel):
    """Embedding 配置模型"""
    name: str
    interface_format: str
    api_key: str
    base_url: str
    model_name: str
    retrieval_k: int = 4


class ProxyConfig(BaseModel):
    """代理配置模型"""
    proxy_url: str = ""
    proxy_port: str = ""
    enabled: bool = False


class WebDAVConfig(BaseModel):
    """WebDAV 配置模型"""
    webdav_url: str = ""
    webdav_username: str = ""
    webdav_password: str = ""


# ============== 小说参数模型 ==============

class NovelParams(BaseModel):
    """小说参数模型"""
    topic: str
    genre: str = "玄幻"
    num_chapters: int = 10
    word_number: int = 3000
    filepath: str
    user_guidance: str = ""
    characters_involved: str = ""
    key_items: str = ""
    scene_location: str = ""
    time_constraint: str = ""
    chapter_num: int = 1


# ============== 生成请求模型 ==============

class GenerateArchitectureRequest(BaseModel):
    """生成架构请求"""
    params: NovelParams
    llm_config_name: str


class GenerateBlueprintRequest(BaseModel):
    """生成目录请求"""
    filepath: str
    num_chapters: int
    user_guidance: str = ""
    llm_config_name: str


class GenerateChapterDraftRequest(BaseModel):
    """生成章节草稿请求"""
    filepath: str
    chapter_num: int
    word_number: int
    user_guidance: str = ""
    characters_involved: str = ""
    key_items: str = ""
    scene_location: str = ""
    time_constraint: str = ""
    llm_config_name: str
    embedding_config_name: str


class FinalizeChapterRequest(BaseModel):
    """定稿章节请求"""
    filepath: str
    chapter_num: int
    word_number: int = 0
    llm_config_name: str
    embedding_config_name: str


class ConsistencyCheckRequest(BaseModel):
    """一致性检查请求"""
    filepath: str
    chapter_num: int
    llm_config_name: str


class ImportKnowledgeRequest(BaseModel):
    """导入知识库请求"""
    filepath: str
    content: str
    embedding_config_name: str


# ============== 响应模型 ==============

class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str


class ConfigResponse(BaseModel):
    """配置响应"""
    llm_configs: Dict[str, LLMConfig]
    embedding_configs: Dict[str, EmbeddingConfig]
    choose_configs: Dict[str, str]
    other_params: Dict[str, Any]
    proxy_setting: ProxyConfig
    webdav_config: WebDAVConfig


class FileContentResponse(BaseModel):
    """文件内容响应"""
    filepath: str
    filename: str
    content: str
    exists: bool


class ChapterListResponse(BaseModel):
    """章节列表响应"""
    filepath: str
    chapters: List[Dict[str, Any]]


class RoleLibraryResponse(BaseModel):
    """角色库响应"""
    filepath: str
    roles: Dict[str, List[str]]


class BatchGenerateRequest(BaseModel):
    """批量生成请求"""
    filepath: str
    start_chapter: int
    end_chapter: int
    word_number: int
    min_word_number: int
    auto_enrich: bool = True
    llm_config_name: str
    embedding_config_name: str


class BuildPromptRequest(BaseModel):
    """构建提示词请求"""
    filepath: str
    chapter_num: int
    word_number: int
    user_guidance: str = ""
    characters_involved: str = ""
    key_items: str = ""
    scene_location: str = ""
    time_constraint: str = ""
    llm_config_name: str
    embedding_config_name: str


class BuildPromptResponse(BaseModel):
    """构建提示词响应"""
    task_id: str
    prompt_text: Optional[str] = None
    message: str


class EnrichChapterRequest(BaseModel):
    """扩写章节请求"""
    chapter_text: str
    word_number: int
    llm_config_name: str


class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    llm_configs: Optional[Dict[str, LLMConfig]] = None
    embedding_configs: Optional[Dict[str, EmbeddingConfig]] = None
    choose_configs: Optional[Dict[str, str]] = None
    other_params: Optional[NovelParams] = None
    proxy_setting: Optional[ProxyConfig] = None
    webdav_config: Optional[WebDAVConfig] = None


class MessageResponse(BaseModel):
    """通用消息响应"""
    status: str
    message: str
