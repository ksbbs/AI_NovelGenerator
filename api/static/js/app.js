// api/static/js/app.js
// AI Novel Generator 前端 JavaScript

// 全局变量
let activeTasks = {};
let pollingInterval = null;
let currentPrompt = null;

// ============== 初始化 ==============

function initApp() {
    console.log('AI Novel Generator initialized');
    loadConfig();
    startTaskPolling();

    // 自动保存参数
    window.addEventListener('beforeunload', function() {
        // 页面关闭前可以做一些清理工作
    });
}

function loadConfig() {
    fetch('/api/config')
        .then(response => response.json())
        .then(config => {
            window.globalConfig = config;
            console.log('Config loaded');
        })
        .catch(error => {
            log('加载配置失败: ' + error.message);
        });
}

// ============== 日志系统 ==============

function log(message) {
    const logDiv = document.getElementById('logOutput');
    if (!logDiv) return;

    const time = new Date().toLocaleTimeString('zh-CN', {hour12: false});
    const line = document.createElement('div');
    line.className = 'mb-1';
    line.innerHTML = `<span class="text-zinc-500">[${time}]</span> ${message}`;
    logDiv.appendChild(line);
    logDiv.scrollTop = logDiv.scrollHeight;
}

function clearLog() {
    const logDiv = document.getElementById('logOutput');
    if (logDiv) {
        logDiv.innerHTML = '';
    }
}

// ============== 任务系统 ==============

function startTaskPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    pollingInterval = setInterval(pollTasks, 2000);
}

function stopTaskPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

async function pollTasks() {
    try {
        const response = await fetch('/api/tasks/running');
        const data = await response.json();

        data.tasks.forEach(task => updateTaskStatusUI(task));

        // 如果没有运行中的任务了，隐藏进度指示器
        if (data.tasks.length === 0) {
            hideTaskIndicator();
        }
    } catch (error) {
        console.error('Polling tasks failed:', error);
    }
}

function updateTaskStatusUI(task) {
    const taskIndicator = document.getElementById('taskIndicator');
    const taskMessage = document.getElementById('taskMessage');

    if (taskIndicator && taskMessage) {
        taskIndicator.classList.remove('hidden');
        taskMessage.textContent = task.message;

        if (task.status === 'completed') {
            log(`✅ ${task.message}`);
        } else if (task.status === 'failed') {
            log(`❌ ${task.message}: ${task.error}`);
        } else {
            log(`⏳ ${task.message}`);
        }
    }
}

function showTaskIndicator(message) {
    const taskIndicator = document.getElementById('taskIndicator');
    const taskMessage = document.getElementById('taskMessage');
    if (taskIndicator && taskMessage) {
        taskIndicator.classList.remove('hidden');
        taskMessage.textContent = message;
    }
}

function hideTaskIndicator() {
    const taskIndicator = document.getElementById('taskIndicator');
    if (taskIndicator) {
        taskIndicator.classList.add('hidden');
    }
}

// ============== 参数管理 ==============

async function saveParams() {
    const params = {
        topic: document.getElementById('topic').value,
        genre: document.getElementById('genre').value,
        num_chapters: parseInt(document.getElementById('numChapters').value),
        word_number: parseInt(document.getElementById('wordNumber').value),
        filepath: document.getElementById('filepath').value,
        chapter_num: document.getElementById('chapterNum').value,
        user_guidance: document.getElementById('userGuidance').value,
        characters_involved: document.getElementById('charactersInvolved').value,
        key_items: document.getElementById('keyItems').value,
        scene_location: document.getElementById('sceneLocation').value,
        time_constraint: document.getElementById('timeConstraint').value
    };

    await fetch('/api/config/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({other_params: params})
    });

    log('参数已保存');
    window.CURRENT_FILEPATH = params.filepath;
}

// ============== 章节内容 ==============

function saveChapterContent() {
    const content = document.getElementById('chapterContent').value;
    const filepath = document.getElementById('filepath').value;
    const chapterNum = document.getElementById('chapterNum').value;

    fetch('/api/file/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            filepath: filepath,
            filename: `chapters/chapter_${chapterNum}.txt`,
            content: content
        })
    })
    .then(response => response.json())
    .then(result => {
        log(result.message);
    })
    .catch(error => {
        log('保存失败: ' + error.message);
    });
}

// ============== 生成架构 ==============

async function generateArchitecture() {
    await saveParams();
    const filepath = document.getElementById('filepath').value;

    const request = {
        params: {
            topic: document.getElementById('topic').value,
            genre: document.getElementById('genre').value,
            num_chapters: parseInt(document.getElementById('numChapters').value),
            word_number: parseInt(document.getElementById('wordNumber').value),
            filepath: filepath,
            user_guidance: document.getElementById('userGuidance').value
        },
        llm_config_name: 'architecture_llm'
    };

    log('🏗️ 正在生成小说架构...');
    const response = await fetch('/api/generate/architecture', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    const data = await response.json();
    if (data.task_id) {
        activeTasks[data.task_id] = 'generateArchitecture';
    }
}

// ============== 生成目录 ==============

async function generateBlueprint() {
    const filepath = document.getElementById('filepath').value;
    const numChapters = parseInt(document.getElementById('numChapters').value);

    const request = {
        filepath: filepath,
        num_chapters: numChapters,
        user_guidance: document.getElementById('userGuidance').value,
        llm_config_name: 'chapter_outline_llm'
    };

    log('📋 正在生成章节目录...');
    const response = await fetch('/api/generate/blueprint', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    const data = await response.json();
    if (data.task_id) {
        activeTasks[data.task_id] = 'generateBlueprint';
    }
}

// ============== 构建提示词 ==============

async function buildChapterPrompt() {
    const filepath = document.getElementById('filepath').value;
    const chapterNum = parseInt(document.getElementById('chapterNum').value);

    const request = {
        filepath: filepath,
        chapter_num: chapterNum,
        word_number: parseInt(document.getElementById('wordNumber').value),
        user_guidance: document.getElementById('userGuidance').value,
        characters_involved: document.getElementById('charactersInvolved').value,
        key_items: document.getElementById('keyItems').value,
        scene_location: document.getElementById('sceneLocation').value,
        time_constraint: document.getElementById('timeConstraint').value,
        llm_config_name: 'prompt_draft_llm',
        embedding_config_name: 'embedding_default'
    };

    log('🔍 正在构建章节提示词...');
    const response = await fetch('/api/generate/build-prompt', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    const data = await response.json();

    if (data.task_id) {
        showTaskIndicator('正在构建提示词...');

        // 定期检查任务完成状态
        const checkInterval = setInterval(async () => {
            const statusResponse = await fetch(`/api/task/${data.task_id}`);
            const status = await statusResponse.json();

            if (status.status === 'completed' && status.result && status.result.prompt_text) {
                clearInterval(checkInterval);
                showPromptEditor(status.result.prompt_text);
                hideTaskIndicator();
                log('✅ 提示词构建完成');
            } else if (status.status === 'failed') {
                clearInterval(checkInterval);
                hideTaskIndicator();
                log('❌ 提示词构建失败: ' + status.error);
            }
        }, 2000);
    }
}

function showPromptEditor(promptText) {
    const editor = document.getElementById('promptEditor');
    const textarea = document.getElementById('promptText');

    if (editor && textarea) {
        editor.classList.remove('hidden');
        textarea.value = promptText;
        updatePromptWordCount();
    }
}

function hidePromptEditor() {
    const editor = document.getElementById('promptEditor');
    if (editor) {
        editor.classList.add('hidden');
    }
}

function updatePromptWordCount() {
    const textarea = document.getElementById('promptText');
    const counter = document.getElementById('promptWordCount');
    if (textarea && counter) {
        counter.textContent = `字数: ${textarea.value.length}`;
    }
}

document.getElementById('promptText')?.addEventListener('input', updatePromptWordCount);

function usePromptForGeneration() {
    const promptText = document.getElementById('promptText')?.value;
    if (promptText) {
        currentPrompt = promptText;
        hidePromptEditor();
        log('✓ 提示词已更新，点击"生成草稿"后使用');
    }
}

// ============== 生成章节草稿 ==============

async function generateChapterDraft() {
    await saveParams();
    const filepath = document.getElementById('filepath').value;
    const chapterNum = parseInt(document.getElementById('chapterNum').value);

    const request = {
        filepath: filepath,
        chapter_num: chapterNum,
        word_number: parseInt(document.getElementById('wordNumber').value),
        user_guidance: document.getElementById('userGuidance').value,
        characters_involved: document.getElementById('charactersInvolved').value,
        key_items: document.getElementById('keyItems').value,
        scene_location: document.getElementById('sceneLocation').value,
        time_constraint: document.getElementById('timeConstraint').value,
        llm_config_name: 'prompt_draft_llm',
        embedding_config_name: 'embedding_default'
    };

    log('📝 正在生成第 ' + chapterNum + ' 章草稿...');
    const response = await fetch('/api/generate/chapter-draft', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    const data = await response.json();

    if (data.task_id) {
        activeTasks[data.task_id] = 'generateChapterDraft';
        // 设置完成后的回调，自动加载章节内容
        setupChapterLoadCallback(data.task_id, chapterNum);
    }
}

function setupChapterLoadCallback(taskId, chapterNum) {
    const checkInterval = setInterval(async () => {
        const response = await fetch(`/api/task/${taskId}`);
        const task = await response.json();

        if (task.status === 'completed') {
            clearInterval(checkInterval);
            loadChapterContent(chapterNum);
        } else if (task.status === 'failed') {
            clearInterval(checkInterval);
        }
    }, 2000);

    // 5分钟后停止检查
    setTimeout(() => clearInterval(checkInterval), 300000);
}

function loadChapterContent(chapterNum) {
    const filepath = document.getElementById('filepath').value;
    fetch(`/api/file/content?filepath=${encodeURIComponent(filepath)}&filename=chapters/chapter_${chapterNum}.txt`)
        .then(response => response.json())
        .then(data => {
            if (data.content) {
                document.getElementById('chapterContent').value = data.content;
                updateWordCount();
                document.getElementById('currentChapter').textContent = chapterNum;
                log(`✅ 第 ${chapterNum} 章已加载`);
            }
        })
        .catch(error => {
            log('加载章节失败: ' + error.message);
        });
}

// ============== 定稿章节 ==============

async function finalizeChapter() {
    const filepath = document.getElementById('filepath').value;
    const chapterNum = parseInt(document.getElementById('chapterNum').value);

    // 先保存当前编辑的章节内容
    saveChapterContent();

    const request = {
        filepath: filepath,
        chapter_num: chapterNum,
        word_number: parseInt(document.getElementById('wordNumber').value),
        llm_config_name: 'final_chapter_llm',
        embedding_config_name: 'embedding_default'
    };

    log('📚 正在定稿第 ' + chapterNum + ' 章...');
    const response = await fetch('/api/generate/finalize', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    const data = await response.json();

    if (data.task_id) {
        activeTasks[data.task_id] = 'finalizeChapter';

        // 设置完成后的回调，自动加载更新后的章节内容
        const checkInterval = setInterval(async () => {
            const statusResponse = await fetch(`/api/task/${data.task_id}`);
            const status = await statusResponse.json();

            if (status.status === 'completed') {
                clearInterval(checkInterval);
                loadChapterContent(chapterNum);
            } else if (status.status === 'failed') {
                clearInterval(checkInterval);
            }
        }, 2000);
    }
}

// ============== 批量生成 ==============

function showBatchDialog() {
    const dialog = document.getElementById('batchDialog');
    if (dialog) {
        dialog.classList.remove('hidden');
        dialog.classList.add('flex');
    }
}

function hideBatchDialog() {
    const dialog = document.getElementById('batchDialog');
    if (dialog) {
        dialog.classList.add('hidden');
        dialog.classList.remove('flex');
    }
}

async function executeBatchGenerate() {
    hideBatchDialog();

    const request = {
        filepath: document.getElementById('filepath').value,
        start_chapter: parseInt(document.getElementById('batchStart').value),
        end_chapter: parseInt(document.getElementById('batchEnd').value),
        word_number: parseInt(document.getElementById('batchWordNumber').value),
        min_word_number: parseInt(document.getElementById('batchMinWord').value),
        auto_enrich: document.getElementById('batchAutoEnrich').checked,
        llm_config_name: 'prompt_draft_llm',
        embedding_config_name: 'embedding_default'
    };

    log(`🚀 批量生成: 第 ${request.start_chapter} - ${request.end_chapter} 章`);
    const response = await fetch('/api/generate/batch', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    const data = await response.json();
    if (data.task_id) {
        activeTasks[data.task_id] = 'batchGenerate';
    }
}

// ============== 一致性检查 ==============

async function checkConsistency() {
    const filepath = document.getElementById('filepath').value;
    const chapterNum = parseInt(document.getElementById('chapterNum').value);

    log('🔍 正在检查第 ' + chapterNum + ' 章一致性...');

    const response = await fetch('/api/check/consistency', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            filepath: filepath,
            chapter_num: chapterNum,
            llm_config_name: 'consistency_review_llm'
        })
    });
    const data = await response.json();

    if (data.status === 'success') {
        log('一致性检查结果:\n' + data.result);
    } else {
        log('❌ 一致性检查失败: ' + data.message);
    }
}

// ============== 扩写章节 ==============

async function enrichChapter() {
    const chapterText = document.getElementById('chapterContent').value;
    const wordNumber = parseInt(document.getElementById('wordNumber').value);

    if (!chapterText) {
        log('请先输入或生成章节内容');
        return;
    }

    log('✏️ 正在扩写章节...');

    const response = await fetch('/api/generate/enrich', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            chapter_text: chapterText,
            word_number: wordNumber,
            llm_config_name: 'final_chapter_llm'
        })
    });
    const data = await response.json();

    if (data.status === 'success') {
        document.getElementById('chapterContent').value = data.result;
        updateWordCount();
        log('✅ 章节扩写完成');
    } else {
        log('❌ 扩写失败: ' + data.message);
    }
}

// ============== 知识库管理 ==============

function showKnowledgeImport() {
    const dialog = document.getElementById('knowledgeDialog');
    if (dialog) {
        dialog.classList.remove('hidden');
        dialog.classList.add('flex');
        document.getElementById('knowledgeContent').focus();
    }
}

function hideKnowledgeImport() {
    const dialog = document.getElementById('knowledgeDialog');
    if (dialog) {
        dialog.classList.add('hidden');
        dialog.classList.remove('flex');
    }
}

async function executeKnowledgeImport() {
    const content = document.getElementById('knowledgeContent').value;
    const filepath = document.getElementById('filepath').value;

    if (!content) {
        log('请输入知识库内容');
        return;
    }

    hideKnowledgeImport();
    log('📂 正在导入知识库...');

    const response = await fetch('/api/knowledge/import', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            filepath: filepath,
            content: content,
            embedding_config_name: 'embedding_default'
        })
    });
    const data = await response.json();

    if (data.status === 'success') {
        log('✅ 知识库导入成功');
    } else {
        log('❌ 导入失败: ' + data.message);
    }
}

async function showVectorstoreClear() {
    if (!confirm('确定要清空向量库吗？此操作不可恢复！')) return;

    const filepath = document.getElementById('filepath').value;
    log('🗑️ 正在清空向量库...');

    const response = await fetch('/api/knowledge/clear', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({filepath: filepath})
    });
    const data = await response.json();

    if (data.status === 'success') {
        log('✅ 向量库已清空');
    } else {
        log('❌ 清空失败: ' + data.message);
    }
}
