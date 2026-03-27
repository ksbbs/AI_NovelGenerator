# web_app.py
# -*- coding: utf-8 -*-
"""
AI小说生成器 Web 版本
使用 Gradio 构建 Web 界面，支持登录认证
"""
import os
import json
import logging
from typing import Optional, Tuple
import gradio as gr
from functools import wraps

# 导入原有模块
from config_manager import load_config, save_config, create_config
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter
from novel_generator import (
    Novel_architecture_generate,
    Chapter_blueprint_generate,
    generate_chapter_draft,
    finalize_chapter,
    import_knowledge_file,
    clear_vector_store,
    build_chapter_prompt
)
from consistency_checker import check_consistency
from utils import read_file, save_string_to_txt, clear_file_content

# 配置日志
logging.basicConfig(
    filename='web_app.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==================== 认证配置 ====================
# 从环境变量读取，或使用默认值
ADMIN_USERNAME = os.environ.get("APP_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("APP_PASSWORD", "novel123")

def auth_function(username: str, password: str) -> bool:
    """认证函数"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

# ==================== 配置管理 ====================
# 支持从环境变量读取配置文件路径，用于 Docker 部署
CONFIG_FILE = os.environ.get("CONFIG_PATH", "config.json")

# 数据存储路径（持久化目录）
DATA_DIR = os.environ.get("DATA_DIR", "/app/novels")

def get_config() -> dict:
    """获取配置"""
    # 确保配置文件目录存在
    config_dir = os.path.dirname(CONFIG_FILE)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    return load_config(CONFIG_FILE)

def update_config(config_data: dict) -> str:
    """更新配置"""
    if save_config(config_data, CONFIG_FILE):
        return "✅ 配置已保存"
    return "❌ 配置保存失败"

# ==================== 辅助函数 ====================
def get_llm_config_from_loaded(loaded_config: dict, config_name: str) -> dict:
    """从加载的配置中获取指定LLM配置"""
    if config_name in loaded_config.get("llm_configs", {}):
        return loaded_config["llm_configs"][config_name]
    # 返回第一个配置
    if loaded_config.get("llm_configs"):
        return next(iter(loaded_config["llm_configs"].values()))
    return {}

def get_embedding_config(loaded_config: dict, config_name: str = None) -> dict:
    """获取Embedding配置"""
    if config_name and config_name in loaded_config.get("embedding_configs", {}):
        return loaded_config["embedding_configs"][config_name]
    if loaded_config.get("embedding_configs"):
        return next(iter(loaded_config["embedding_configs"].values()))
    return {}

def safe_get_int(value, default=1):
    """安全获取整数值"""
    try:
        return int(value)
    except:
        return default

# ==================== 业务逻辑函数 ====================
def generate_architecture_handler(
    topic: str,
    genre: str,
    num_chapters: int,
    word_number: int,
    filepath: str,
    user_guidance: str,
    llm_config_name: str,
    progress=gr.Progress()
) -> Tuple[str, str]:
    """生成小说架构"""
    if not filepath:
        return "", "❌ 请先设置保存路径"

    try:
        config = get_config()
        llm_conf = get_llm_config_from_loaded(config, llm_config_name)

        if not llm_conf.get("api_key"):
            return "", "❌ 请先配置API Key"

        progress(0.1, desc="开始生成小说架构...")

        Novel_architecture_generate(
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            api_key=llm_conf.get("api_key"),
            base_url=llm_conf.get("base_url"),
            llm_model=llm_conf.get("model_name"),
            topic=topic,
            genre=genre,
            number_of_chapters=num_chapters,
            word_number=word_number,
            filepath=filepath,
            temperature=llm_conf.get("temperature", 0.7),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600),
            user_guidance=user_guidance
        )

        # 读取生成的架构文件
        arch_file = os.path.join(filepath, "Novel_architecture.txt")
        arch_content = read_file(arch_file)

        progress(1.0, desc="完成！")
        return arch_content, "✅ 小说架构生成完成"
    except Exception as e:
        logging.error(f"生成小说架构失败: {str(e)}")
        return "", f"❌ 生成失败: {str(e)}"

def generate_blueprint_handler(
    filepath: str,
    num_chapters: int,
    user_guidance: str,
    llm_config_name: str,
    progress=gr.Progress()
) -> Tuple[str, str]:
    """生成章节蓝图"""
    if not filepath:
        return "", "❌ 请先设置保存路径"

    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if not os.path.exists(arch_file):
        return "", "❌ 请先生成小说架构"

    try:
        config = get_config()
        llm_conf = get_llm_config_from_loaded(config, llm_config_name)

        progress(0.1, desc="开始生成章节蓝图...")

        Chapter_blueprint_generate(
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            api_key=llm_conf.get("api_key"),
            base_url=llm_conf.get("base_url"),
            llm_model=llm_conf.get("model_name"),
            filepath=filepath,
            number_of_chapters=num_chapters,
            temperature=llm_conf.get("temperature", 0.7),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600),
            user_guidance=user_guidance
        )

        # 读取生成的蓝图文件
        blueprint_file = os.path.join(filepath, "Novel_directory.txt")
        blueprint_content = read_file(blueprint_file)

        progress(1.0, desc="完成！")
        return blueprint_content, "✅ 章节蓝图生成完成"
    except Exception as e:
        logging.error(f"生成章节蓝图失败: {str(e)}")
        return "", f"❌ 生成失败: {str(e)}"

def generate_chapter_handler(
    filepath: str,
    chapter_num: int,
    word_number: int,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    llm_config_name: str,
    embedding_config_name: str,
    custom_prompt: str,
    progress=gr.Progress()
) -> Tuple[str, str]:
    """生成章节草稿"""
    if not filepath:
        return "", "❌ 请先设置保存路径"

    try:
        config = get_config()
        llm_conf = get_llm_config_from_loaded(config, llm_config_name)
        emb_conf = get_embedding_config(config, embedding_config_name)

        progress(0.1, desc="准备生成章节草稿...")

        draft_text = generate_chapter_draft(
            api_key=llm_conf.get("api_key"),
            base_url=llm_conf.get("base_url"),
            model_name=llm_conf.get("model_name"),
            filepath=filepath,
            novel_number=chapter_num,
            word_number=word_number,
            temperature=llm_conf.get("temperature", 0.7),
            user_guidance=user_guidance,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            embedding_api_key=emb_conf.get("api_key"),
            embedding_url=emb_conf.get("base_url"),
            embedding_interface_format=emb_conf.get("interface_format", "OpenAI"),
            embedding_model_name=emb_conf.get("model_name"),
            embedding_retrieval_k=emb_conf.get("retrieval_k", 4),
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600),
            custom_prompt_text=custom_prompt if custom_prompt else None
        )

        progress(1.0, desc="完成！")
        return draft_text, f"✅ 第{chapter_num}章草稿生成完成"
    except Exception as e:
        logging.error(f"生成章节失败: {str(e)}")
        return "", f"❌ 生成失败: {str(e)}"

def finalize_chapter_handler(
    filepath: str,
    chapter_num: int,
    word_number: int,
    chapter_content: str,
    llm_config_name: str,
    embedding_config_name: str,
    progress=gr.Progress()
) -> Tuple[str, str]:
    """定稿章节"""
    if not filepath:
        return "", "❌ 请先设置保存路径"

    try:
        config = get_config()
        llm_conf = get_llm_config_from_loaded(config, llm_config_name)
        emb_conf = get_embedding_config(config, embedding_config_name)

        progress(0.1, desc="开始定稿...")

        # 保存编辑后的内容
        chapters_dir = os.path.join(filepath, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")
        clear_file_content(chapter_file)
        save_string_to_txt(chapter_content, chapter_file)

        finalize_chapter(
            novel_number=chapter_num,
            word_number=word_number,
            api_key=llm_conf.get("api_key"),
            base_url=llm_conf.get("base_url"),
            model_name=llm_conf.get("model_name"),
            temperature=llm_conf.get("temperature", 0.7),
            filepath=filepath,
            embedding_api_key=emb_conf.get("api_key"),
            embedding_url=emb_conf.get("base_url"),
            embedding_interface_format=emb_conf.get("interface_format", "OpenAI"),
            embedding_model_name=emb_conf.get("model_name"),
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600)
        )

        # 读取定稿后的内容
        final_text = read_file(chapter_file)

        progress(1.0, desc="完成！")
        return final_text, f"✅ 第{chapter_num}章定稿完成"
    except Exception as e:
        logging.error(f"定稿失败: {str(e)}")
        return chapter_content, f"❌ 定稿失败: {str(e)}"

def consistency_check_handler(
    filepath: str,
    chapter_num: int,
    llm_config_name: str,
    progress=gr.Progress()
) -> str:
    """一致性检查"""
    if not filepath:
        return "❌ 请先设置保存路径"

    try:
        config = get_config()
        llm_conf = get_llm_config_from_loaded(config, llm_config_name)

        chap_file = os.path.join(filepath, "chapters", f"chapter_{chapter_num}.txt")
        chapter_text = read_file(chap_file)

        if not chapter_text.strip():
            return "❌ 当前章节文件为空或不存在"

        progress(0.1, desc="开始一致性检查...")

        result = check_consistency(
            novel_setting=read_file(os.path.join(filepath, "Novel_architecture.txt")),
            character_state=read_file(os.path.join(filepath, "character_state.txt")),
            global_summary=read_file(os.path.join(filepath, "global_summary.txt")),
            chapter_text=chapter_text,
            api_key=llm_conf.get("api_key"),
            base_url=llm_conf.get("base_url"),
            model_name=llm_conf.get("model_name"),
            temperature=llm_conf.get("temperature", 0.7),
            interface_format=llm_conf.get("interface_format", "OpenAI"),
            max_tokens=llm_conf.get("max_tokens", 8192),
            timeout=llm_conf.get("timeout", 600),
            plot_arcs=""
        )

        progress(1.0, desc="完成！")
        return result
    except Exception as e:
        logging.error(f"一致性检查失败: {str(e)}")
        return f"❌ 检查失败: {str(e)}"

def load_file_content(filepath: str, filename: str) -> str:
    """加载文件内容"""
    if not filepath:
        return ""
    file_path = os.path.join(filepath, filename)
    if os.path.exists(file_path):
        return read_file(file_path)
    return ""

def save_file_content(filepath: str, filename: str, content: str) -> str:
    """保存文件内容"""
    if not filepath:
        return "❌ 请先设置保存路径"
    file_path = os.path.join(filepath, filename)
    try:
        clear_file_content(file_path)
        save_string_to_txt(content, file_path)
        return "✅ 保存成功"
    except Exception as e:
        return f"❌ 保存失败: {str(e)}"

# ==================== Gradio 界面 ====================
def create_ui():
    """创建Gradio界面"""
    config = get_config()
    llm_config_names = list(config.get("llm_configs", {}).keys())
    embedding_config_names = list(config.get("embedding_configs", {}).keys())

    with gr.Blocks(title="AI小说生成器", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 📖 AI小说生成器 Web版")
        gr.Markdown("基于大语言模型的多功能小说生成工具")

        with gr.Tabs():
            # ========== 主工作台 ==========
            with gr.TabItem("主工作台"):
                with gr.Row():
                    with gr.Column(scale=1):
                        # 基本设置
                        gr.Markdown("### 基本设置")
                        filepath_input = gr.Textbox(label="保存路径", placeholder="/app/novels/my_novel", value=config.get("other_params", {}).get("filepath", ""))

                        with gr.Row():
                            llm_selector = gr.Dropdown(choices=llm_config_names, label="LLM配置", value=llm_config_names[0] if llm_config_names else None)
                            embedding_selector = gr.Dropdown(choices=embedding_config_names, label="Embedding配置", value=embedding_config_names[0] if embedding_config_names else None)

                        # 小说参数
                        gr.Markdown("### 小说参数")
                        topic_input = gr.Textbox(label="主题", lines=3, placeholder="输入小说主题...")
                        genre_input = gr.Textbox(label="类型", value="玄幻")
                        num_chapters_input = gr.Number(label="章节数", value=10)
                        word_number_input = gr.Number(label="每章字数", value=3000)

                        user_guidance_input = gr.Textbox(label="内容指导", lines=3, placeholder="可选的内容指导...")

                    with gr.Column(scale=2):
                        # 操作按钮
                        gr.Markdown("### 生成操作")
                        with gr.Row():
                            gen_arch_btn = gr.Button("Step1: 生成架构", variant="primary")
                            gen_blueprint_btn = gr.Button("Step2: 生成蓝图", variant="primary")

                        status_output = gr.Textbox(label="状态", interactive=False)

                # 架构和蓝图内容
                with gr.Row():
                    architecture_output = gr.Textbox(label="小说架构", lines=15, interactive=True)
                    blueprint_output = gr.Textbox(label="章节蓝图", lines=15, interactive=True)

                with gr.Row():
                    save_arch_btn = gr.Button("保存架构")
                    save_blueprint_btn = gr.Button("保存蓝图")

            # ========== 章节生成 ==========
            with gr.TabItem("章节生成"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 章节设置")
                        chapter_num_input = gr.Number(label="章节号", value=1)

                        with gr.Row():
                            chapter_llm_selector = gr.Dropdown(choices=llm_config_names, label="生成LLM", value=llm_config_names[0] if llm_config_names else None)
                            finalize_llm_selector = gr.Dropdown(choices=llm_config_names, label="定稿LLM", value=llm_config_names[0] if llm_config_names else None)

                        characters_input = gr.Textbox(label="涉及角色", placeholder="角色名称，逗号分隔")
                        key_items_input = gr.Textbox(label="关键道具")
                        scene_input = gr.Textbox(label="场景地点")
                        time_input = gr.Textbox(label="时间约束")

                        custom_prompt_input = gr.Textbox(label="自定义提示词(可选)", lines=5, placeholder="留空则自动生成...")

                        with gr.Row():
                            gen_chapter_btn = gr.Button("生成章节草稿", variant="primary")
                            finalize_btn = gr.Button("定稿当前章节", variant="secondary")
                            check_btn = gr.Button("一致性检查", variant="secondary")

                        chapter_status = gr.Textbox(label="状态", interactive=False)

                    with gr.Column(scale=2):
                        chapter_output = gr.Textbox(label="章节内容", lines=25, interactive=True)
                        consistency_output = gr.Textbox(label="检查结果", lines=5, interactive=False)

            # ========== 章节管理 ==========
            with gr.TabItem("章节管理"):
                gr.Markdown("### 章节文件管理")

                with gr.Row():
                    chapter_list_input = gr.Number(label="章节号", value=1)
                    load_chapter_btn = gr.Button("加载章节")

                chapter_edit = gr.Textbox(label="章节内容", lines=30, interactive=True)

                with gr.Row():
                    save_chapter_btn = gr.Button("保存章节")
                    chapter_file_status = gr.Textbox(label="状态", interactive=False)

            # ========== 配置管理 ==========
            with gr.TabItem("配置管理"):
                gr.Markdown("### 配置文件")

                config_editor = gr.Code(label="config.json", language="json", value=json.dumps(config, ensure_ascii=False, indent=2))

                with gr.Row():
                    save_config_btn = gr.Button("保存配置", variant="primary")
                    reload_config_btn = gr.Button("重新加载")

                config_status = gr.Textbox(label="状态", interactive=False)

        # ========== 事件绑定 ==========
        # 主工作台
        gen_arch_btn.click(
            fn=generate_architecture_handler,
            inputs=[topic_input, genre_input, num_chapters_input, word_number_input, filepath_input, user_guidance_input, llm_selector],
            outputs=[architecture_output, status_output]
        )

        gen_blueprint_btn.click(
            fn=generate_blueprint_handler,
            inputs=[filepath_input, num_chapters_input, user_guidance_input, llm_selector],
            outputs=[blueprint_output, status_output]
        )

        save_arch_btn.click(
            fn=lambda fp, content: save_file_content(fp, "Novel_architecture.txt", content),
            inputs=[filepath_input, architecture_output],
            outputs=[status_output]
        )

        save_blueprint_btn.click(
            fn=lambda fp, content: save_file_content(fp, "Novel_directory.txt", content),
            inputs=[filepath_input, blueprint_output],
            outputs=[status_output]
        )

        # 章节生成
        gen_chapter_btn.click(
            fn=generate_chapter_handler,
            inputs=[
                filepath_input, chapter_num_input, word_number_input, user_guidance_input,
                characters_input, key_items_input, scene_input, time_input,
                chapter_llm_selector, embedding_selector, custom_prompt_input
            ],
            outputs=[chapter_output, chapter_status]
        )

        finalize_btn.click(
            fn=finalize_chapter_handler,
            inputs=[filepath_input, chapter_num_input, word_number_input, chapter_output, finalize_llm_selector, embedding_selector],
            outputs=[chapter_output, chapter_status]
        )

        check_btn.click(
            fn=consistency_check_handler,
            inputs=[filepath_input, chapter_num_input, llm_selector],
            outputs=[consistency_output]
        )

        # 章节管理
        def load_chapter_handler(fp, num):
            return load_file_content(fp, f"chapters/chapter_{safe_get_int(num)}.txt")

        load_chapter_btn.click(
            fn=load_chapter_handler,
            inputs=[filepath_input, chapter_list_input],
            outputs=[chapter_edit]
        )

        save_chapter_btn.click(
            fn=lambda fp, num, content: save_file_content(fp, f"chapters/chapter_{safe_get_int(num)}.txt", content),
            inputs=[filepath_input, chapter_list_input, chapter_edit],
            outputs=[chapter_file_status]
        )

        # 配置管理
        def save_config_handler(config_str):
            try:
                config_data = json.loads(config_str)
                return update_config(config_data)
            except json.JSONDecodeError as e:
                return f"❌ JSON格式错误: {str(e)}"

        def reload_config_handler():
            return json.dumps(get_config(), ensure_ascii=False, indent=2)

        save_config_btn.click(
            fn=save_config_handler,
            inputs=[config_editor],
            outputs=[config_status]
        )

        reload_config_btn.click(
            fn=reload_config_handler,
            outputs=[config_editor]
        )

    return app

# ==================== 主函数 ====================
if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        auth=auth_function,
        auth_message="请输入用户名和密码访问AI小说生成器"
    )
