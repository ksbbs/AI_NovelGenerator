# api/services.py
# -*- coding: utf-8 -*-
"""
业务逻辑层 - 处理小说生成的核心服务
"""
import os
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

# 导入核心模块
from novel_generator import (
    Novel_architecture_generate,
    Chapter_blueprint_generate,
    generate_chapter_draft,
    finalize_chapter,
    import_knowledge_file,
    clear_vector_store,
    enrich_chapter_text,
    build_chapter_prompt
)
from consistency_checker import check_consistency
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter

# 本地导入（避免循环导入）
import config_manager
from utils import read_file, save_string_to_txt, clear_file_content

# 任务跟踪（内存中，生产环境建议使用 Redis）
tasks: Dict[str, Dict[str, Any]] = {}
task_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# 全局服务实例
_service_instance = None


class NovelGenerationService:
    """小说生成服务类"""

    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "config.json")
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """确保配置文件存在"""
        if not os.path.exists(self.config_file):
            config_manager.create_config(self.config_file)
            logging.info(f"Created default config at {self.config_file}")

    def load_config(self) -> dict:
        """加载配置"""
        return config_manager.load_config(self.config_file)

    def save_config(self, config: dict) -> bool:
        """保存配置"""
        return config_manager.save_config(config, self.config_file)

    async def create_task(self, name: str) -> str:
        """创建后台任务并返回 task_id"""
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "name": name,
            "status": "pending",
            "message": "任务已加入队列",
            "result": None,
            "error": None,
            "created_at": str(os.utime(os.getcwd())) if hasattr(os, 'utime') else ""
        }
        return task_id

    async def update_task(self, task_id: str, status: str, message: str = "", result: Any = None, error: str = None):
        """更新任务状态"""
        if task_id in tasks:
            tasks[task_id].update({
                "status": status,
                "message": message,
                "result": result,
                "error": error
            })
            logging.info(f"Task {task_id} updated: {status} - {message}")

    async def run_in_thread(self, func, *args, task_id: str = None, **kwargs):
        """在线程池中运行阻塞函数"""
        loop = asyncio.get_event_loop()
        if task_id:
            await self.update_task(task_id, "running", "任务开始执行")
        try:
            result = await loop.run_in_executor(None, func, *args, **kwargs)
            if task_id:
                await self.update_task(task_id, "completed", "任务完成", result=result)
            return result
        except Exception as e:
            logging.error(f"Error in run_in_thread: {str(e)}", exc_info=True)
            if task_id:
                await self.update_task(task_id, "failed", f"任务失败: {str(e)}", error=str(e))
            raise

    async def generate_architecture(self, request: dict) -> str:
        """生成小说架构"""
        task_id = await self.create_task("generate_architecture")
        asyncio.create_task(self._generate_architecture(request, task_id))
        return task_id

    async def _generate_architecture(self, request: dict, task_id: str):
        """内部：生成小说架构"""
        config = self.load_config()
        params = request.get("params", {})
        llm_config_name = request.get("llm_config_name", "architecture_llm")

        # 从 choose_configs 中获取实际的 LLM 配置名
        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        llm_config = config["llm_configs"].get(actual_llm_name, {})

        await self.run_in_thread(
            Novel_architecture_generate,
            interface_format=llm_config.get("interface_format", "OpenAI"),
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            llm_model=llm_config.get("model_name", ""),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600),
            topic=params.get("topic", ""),
            genre=params.get("genre", "玄幻"),
            number_of_chapters=params.get("num_chapters", 10),
            word_number=params.get("word_number", 3000),
            filepath=params.get("filepath", ""),
            user_guidance=params.get("user_guidance", ""),
            task_id=task_id
        )

    async def generate_blueprint(self, request: dict) -> str:
        """生成章节目录"""
        task_id = await self.create_task("generate_blueprint")
        asyncio.create_task(self._generate_blueprint(request, task_id))
        return task_id

    async def _generate_blueprint(self, request: dict, task_id: str):
        """内部：生成章节目录"""
        config = self.load_config()
        llm_config_name = request.get("llm_config_name", "chapter_outline_llm")
        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        llm_config = config["llm_configs"].get(actual_llm_name, {})

        await self.run_in_thread(
            Chapter_blueprint_generate,
            interface_format=llm_config.get("interface_format", "OpenAI"),
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            llm_model=llm_config.get("model_name", ""),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600),
            number_of_chapters=request.get("num_chapters", 10),
            filepath=request.get("filepath", ""),
            user_guidance=request.get("user_guidance", ""),
            task_id=task_id
        )

    async def generate_chapter_draft(self, request: dict) -> str:
        """生成章节草稿"""
        task_id = await self.create_task("generate_chapter_draft")
        asyncio.create_task(self._generate_chapter_draft(request, task_id))
        return task_id

    async def _generate_chapter_draft(self, request: dict, task_id: str):
        """内部：生成章节草稿"""
        config = self.load_config()
        llm_config_name = request.get("llm_config_name", "prompt_draft_llm")
        embedding_config_name = request.get("embedding_config_name", "OpenAI")

        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        actual_emb_name = embedding_config_name

        llm_config = config["llm_configs"].get(actual_llm_name, {})
        emb_config = config["embedding_configs"].get(actual_emb_name, {})

        result = await self.run_in_thread(
            generate_chapter_draft,
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            model_name=llm_config.get("model_name", ""),
            filepath=request.get("filepath", ""),
            novel_number=request.get("chapter_num", 1),
            word_number=request.get("word_number", 3000),
            temperature=llm_config.get("temperature", 0.7),
            user_guidance=request.get("user_guidance", ""),
            characters_involved=request.get("characters_involved", ""),
            key_items=request.get("key_items", ""),
            scene_location=request.get("scene_location", ""),
            time_constraint=request.get("time_constraint", ""),
            embedding_api_key=emb_config.get("api_key", ""),
            embedding_url=emb_config.get("base_url", ""),
            embedding_interface_format=emb_config.get("interface_format", "OpenAI"),
            embedding_model_name=emb_config.get("model_name", ""),
            embedding_retrieval_k=emb_config.get("retrieval_k", 4),
            interface_format=llm_config.get("interface_format", "OpenAI"),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600),
            task_id=task_id
        )

    async def finalize_chapter(self, request: dict) -> str:
        """定稿章节"""
        task_id = await self.create_task("finalize_chapter")
        asyncio.create_task(self._finalize_chapter(request, task_id))
        return task_id

    async def _finalize_chapter(self, request: dict, task_id: str):
        """内部：定稿章节"""
        config = self.load_config()
        llm_config_name = request.get("llm_config_name", "final_chapter_llm")
        embedding_config_name = request.get("embedding_config_name", "OpenAI")

        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        actual_emb_name = embedding_config_name

        llm_config = config["llm_configs"].get(actual_llm_name, {})
        emb_config = config["embedding_configs"].get(actual_emb_name, {})

        await self.run_in_thread(
            finalize_chapter,
            novel_number=request.get("chapter_num", 1),
            word_number=request.get("word_number", 0),
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            model_name=llm_config.get("model_name", ""),
            temperature=llm_config.get("temperature", 0.7),
            filepath=request.get("filepath", ""),
            embedding_api_key=emb_config.get("api_key", ""),
            embedding_url=emb_config.get("base_url", ""),
            embedding_interface_format=emb_config.get("interface_format", "OpenAI"),
            embedding_model_name=emb_config.get("model_name", ""),
            interface_format=llm_config.get("interface_format", "OpenAI"),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600),
            task_id=task_id
        )

    async def build_prompt(self, request: dict) -> str:
        """构建章节提示词"""
        task_id = await self.create_task("build_prompt")
        asyncio.create_task(self._build_prompt(request, task_id))
        return task_id

    async def _build_prompt(self, request: dict, task_id: str):
        """内部：构建章节提示词"""
        config = self.load_config()
        llm_config_name = request.get("llm_config_name", "prompt_draft_llm")
        embedding_config_name = request.get("embedding_config_name", "OpenAI")

        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        actual_emb_name = embedding_config_name

        llm_config = config["llm_configs"].get(actual_llm_name, {})
        emb_config = config["embedding_configs"].get(actual_emb_name, {})

        result = await self.run_in_thread(
            build_chapter_prompt,
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            model_name=llm_config.get("model_name", ""),
            filepath=request.get("filepath", ""),
            novel_number=request.get("chapter_num", 1),
            word_number=request.get("word_number", 3000),
            temperature=llm_config.get("temperature", 0.7),
            user_guidance=request.get("user_guidance", ""),
            characters_involved=request.get("characters_involved", ""),
            key_items=request.get("key_items", ""),
            scene_location=request.get("scene_location", ""),
            time_constraint=request.get("time_constraint", ""),
            embedding_api_key=emb_config.get("api_key", ""),
            embedding_url=emb_config.get("base_url", ""),
            embedding_interface_format=emb_config.get("interface_format", "OpenAI"),
            embedding_model_name=emb_config.get("model_name", ""),
            embedding_retrieval_k=emb_config.get("retrieval_k", 4),
            interface_format=llm_config.get("interface_format", "OpenAI"),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600),
            task_id=task_id
        )

    async def enrich_chapter(self, chapter_text: str, word_number: int, llm_config_name: str) -> str:
        """扩写章节内容"""
        config = self.load_config()
        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        llm_config = config["llm_configs"].get(actual_llm_name, {})

        result = await self.run_in_thread(
            enrich_chapter_text,
            chapter_text=chapter_text,
            word_number=word_number,
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            model_name=llm_config.get("model_name", ""),
            temperature=llm_config.get("temperature", 0.7),
            interface_format=llm_config.get("interface_format", "OpenAI"),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600)
        )
        return result

    async def check_consistency(self, filepath: str, chapter_num: int, llm_config_name: str) -> str:
        """一致性检查"""
        config = self.load_config()
        actual_llm_name = config.get("choose_configs", {}).get(llm_config_name, list(config.get("llm_configs", {}).keys())[0] if config.get("llm_configs") else "")
        llm_config = config["llm_configs"].get(actual_llm_name, {})

        # 读取文件
        novel_setting = read_file(os.path.join(filepath, "Novel_architecture.txt"))
        character_state = read_file(os.path.join(filepath, "character_state.txt"))
        global_summary = read_file(os.path.join(filepath, "global_summary.txt"))
        chapter_text = read_file(os.path.join(filepath, "chapters", f"chapter_{chapter_num}.txt"))
        plot_arcs = read_file(os.path.join(filepath, "plot_arcs.txt"))

        result = await self.run_in_thread(
            check_consistency,
            novel_setting=novel_setting or "",
            character_state=character_state or "",
            global_summary=global_summary or "",
            chapter_text=chapter_text or "",
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url", ""),
            model_name=llm_config.get("model_name", ""),
            temperature=0.3,
            plot_arcs=plot_arcs or "",
            interface_format=llm_config.get("interface_format", "OpenAI"),
            max_tokens=llm_config.get("max_tokens", 8192),
            timeout=llm_config.get("timeout", 600)
        )
        return result

    async def import_knowledge(self, filepath: str, content: str, embedding_config_name: str) -> bool:
        """导入知识库"""
        config = self.load_config()
        actual_emb_name = embedding_config_name
        emb_config = config["embedding_configs"].get(actual_emb_name, {})

        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as temp:
            temp.write(content)
            temp_path = temp.name

        try:
            result = await self.run_in_thread(
                import_knowledge_file,
                embedding_api_key=emb_config.get("api_key", ""),
                embedding_url=emb_config.get("base_url", ""),
                embedding_interface_format=emb_config.get("interface_format", "OpenAI"),
                embedding_model_name=emb_config.get("model_name", ""),
                file_path=temp_path,
                filepath=filepath
            )
            return result
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass

    async def clear_vectorstore(self, filepath: str) -> bool:
        """清空向量库"""
        result = await self.run_in_thread(
            clear_vector_store,
            filepath
        )
        return result

    async def batch_generate(self, request: dict) -> str:
        """批量生成章节"""
        task_id = await self.create_task("batch_generate")
        asyncio.create_task(self._batch_generate(request, task_id))
        return task_id

    async def _batch_generate(self, request: dict, task_id: str):
        """内部：批量生成章节"""
        config = self.load_config()
        start = request.get("start_chapter", 1)
        end = request.get("end_chapter", 1)
        filepath = request.get("filepath", "")

        total = end - start + 1
        for i in range(start, end + 1):
            await self.update_task(task_id, "running", f"正在生成第 {i}/{end} 章 ({total} 章中)")

            # 生成草稿
            draft_request = {
                "filepath": filepath,
                "chapter_num": i,
                "word_number": request.get("word_number", 3000),
                "user_guidance": request.get("user_guidance", ""),
                "characters_involved": request.get("characters_involved", ""),
                "key_items": request.get("key_items", ""),
                "scene_location": request.get("scene_location", ""),
                "time_constraint": request.get("time_constraint", ""),
                "llm_config_name": request.get("llm_config_name", "prompt_draft_llm"),
                "embedding_config_name": request.get("embedding_config_name", "OpenAI")
            }
            await self._generate_chapter_draft(draft_request, None)

            # 定稿
            finalize_request = {
                "filepath": filepath,
                "chapter_num": i,
                "word_number": request.get("word_number", 3000),
                "llm_config_name": request.get("llm_config_name", "final_chapter_llm"),
                "embedding_config_name": request.get("embedding_config_name", "OpenAI")
            }
            await self._finalize_chapter(finalize_request, None)

        await self.update_task(task_id, "completed", f"批量生成完成，共生成 {total} 章")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return tasks.get(task_id)

    def get_all_running_tasks(self) -> list:
        """获取所有运行中的任务"""
        return [
            {**task_info, "task_id": task_id}
            for task_id, task_info in tasks.items()
            if task_info.get("status") in ["running", "pending"]
        ]

    def get_file_content(self, filepath: str, filename: str) -> str:
        """获取文件内容"""
        full_path = os.path.join(filepath, filename)
        return read_file(full_path)

    def save_file_content(self, filepath: str, filename: str, content: str) -> bool:
        """保存文件内容"""
        full_path = os.path.join(filepath, filename)
        return save_string_to_txt(content, full_path)

    def list_chapters(self, filepath: str) -> list:
        """列出所有章节"""
        chapters_dir = os.path.join(filepath, "chapters")
        chapters = []
        if os.path.exists(chapters_dir):
            for f in sorted(os.listdir(chapters_dir)):
                if f.endswith(".txt"):
                    chapter_num = int(f.replace("chapter_", "").replace(".txt", ""))
                    chapters.append({
                        "num": chapter_num,
                        "file": f,
                        "path": os.path.join(chapters_dir, f)
                    })
        return sorted(chapters, key=lambda x: x["num"])

    def list_role_library(self, filepath: str) -> dict:
        """列出角色库"""
        role_lib_path = os.path.join(filepath, "角色库")
        roles = {}
        if os.path.exists(role_lib_path):
            for category in os.listdir(role_lib_path):
                cat_path = os.path.join(role_lib_path, category)
                if os.path.isdir(cat_path):
                    roles[category] = [
                        f.replace(".txt", "")
                        for f in os.listdir(cat_path)
                        if f.endswith(".txt")
                    ]
        return roles

    def get_role_content(self, filepath: str, category: str, role_name: str) -> str:
        """获取角色内容"""
        role_file = os.path.join(filepath, "角色库", category, f"{role_name}.txt")
        return read_file(role_file)

    def save_role_content(self, filepath: str, category: str, role_name: str, content: str) -> bool:
        """保存角色内容"""
        category_dir = os.path.join(filepath, "角色库", category)
        os.makedirs(category_dir, exist_ok=True)
        role_file = os.path.join(category_dir, f"{role_name}.txt")
        return save_string_to_txt(content, role_file)

    def delete_role(self, filepath: str, category: str, role_name: str) -> bool:
        """删除角色"""
        role_file = os.path.join(filepath, "角色库", category, f"{role_name}.txt")
        try:
            os.remove(role_file)
            # 如果目录为空，则删除目录
            category_dir = os.path.dirname(role_file)
            if os.listdir(category_dir):
                return True
            os.rmdir(category_dir)
            return True
        except:
            return False


# ============== 服务实例管理 ==============

def initialize_service(data_dir: str = None) -> NovelGenerationService:
    """初始化服务实例"""
    global _service_instance
    if data_dir is None:
        data_dir = os.getenv("DATA_DIR", "/app/data")
    if _service_instance is None:
        _service_instance = NovelGenerationService(data_dir)
    return _service_instance


def get_service() -> NovelGenerationService:
    """获取服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = NovelGenerationService(os.getenv("DATA_DIR", "/app/data"))
    return _service_instance
