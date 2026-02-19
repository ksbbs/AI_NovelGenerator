# AI Novel Generator Web 版部署指南

本文档介绍如何部署AI Novel Generator的Web版本（适合Docker环境）。

## 目录

- [快速开始](#快速开始)
- [Docker部署](#docker部署)
- [本地开发](#本地开发)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 一键启动

```bash
# 克隆仓库
git clone https://github.com/ksbbs/AI_NovelGenerator.git
cd AI_NovelGenerator
git checkout dockerweb

# 启动服务
docker-compose up -d

# 访问应用
open http://localhost:8000
```

## Docker部署

### 方式一：使用 docker-compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据卷（谨慎！）
docker-compose down -v
```

### 方式二：使用 Docker CLI

```bash
# 构建镜像
docker build -t ai-novel-generator .

# 运行容器（挂载数据目录）
docker run -d \
  --name ai-novel-generator \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  ai-novel-generator

# 查看日志
docker logs -f ai-novel-generator

# 停止容器
docker stop ai-novel-generator

# 启动容器
docker start ai-novel-generator
```

### 方式三：使用自定义数据目录

```bash
# 创建数据目录
mkdir -p /path/to/your/data

# 运行容器
docker run -d \
  --name ai-novel-generator \
  -p 8000:8000 \
  -v /path/to/your/data:/app/data \
  ai-novel-generator
```

## 本地开发

### 前置要求

- Python 3.12+
- pip

### 安装依赖

```bash
# 安装依赖
pip install -r requirements.txt
```

### 启动服务

```bash
# 开发模式启动（自动重载）
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 或使用默认设置
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 访问应用

打开浏览器访问：`http://localhost:8000`

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATA_DIR` | `/app/data` | 数据存储目录 |
| `PYTHONUNBUFFERED` | `1` | Python输出不缓冲 |

### 配置文件位置

配置文件 `config.json` 生成在数据目录中：
- Docker环境：`宿主挂载的目录/config.json`
- 本地开发：`/app/data/config.json`

### 首次使用流程

1. **配置LLM**
   - 访问 `http://localhost:8000/config`
   - 点击"新增配置"添加你的LLM配置
   - 支持的格式：OpenAI、DeepSeek、Gemini、Ollama等

2. **配置Embedding**
   - 在配置页面添加Embedding模型配置
   - 用于向量检索和语义搜索

3. **设置小说参数**
   - 返回主页
   - 填写小说参数（主题、类型、章节等）
   - 点击"保存参数"

4. **生成小说**
   - 点击"生成架构"创建小说世界观
   - 点击"生成目录"创建章节大纲
   - 点击"构建提示词"生成章节提示词（可选编辑）
   - 点击"生成草稿"生成章节内容
   - 点击"定稿章节"完成章节并更新向量库

## 常见问题

### 1. 端口被占用

```bash
# 修改 docker-compose.yml 中的端口映射
# 将 "8000:8000" 改为 "其他端口:8000"
```

### 2. 跨域问题

FastAPI默认允许跨域，如需自定义，编辑 `api/main.py` 添加：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. 数据持久化

数据存储在Docker volume中，重启容器不会丢失：

```bash
# 查看volumes
docker volume ls

# 查看特定volume
docker volume inspect novel-data

# 备份数据
docker run --rm -v novel-data:/data -v $(pwd):/backup ubuntu \
  tar czf /backup/novel-data-backup.tar.gz /data
```

### 4. 资源限制

编辑 `docker-compose.yml` 添加资源限制：

```yaml
services:
  ai-novel-generator:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### 5. 多实例部署

```bash
# 运行多个实例
docker run -d --name ai-novel-gen-1 -p 8000:8000 -v ./data1:/app/data ai-novel-generator
docker run -d --name ai-novel-gen-2 -p 8001:8000 -v ./data2:/app/data ai-novel-generator
```

### 6. 监控和日志

```bash
# 实时日志
docker-compose logs -f

# 查看应用日志
docker exec ai-novel-generator tail -f app.log

# 健康检查
curl http://localhost:8000/health
```

### 7. 升级到最新版本

```bash
# 拉取最新代码
git fetch origin
git checkout dockerweb
git pull origin dockerweb

# 重新构建并运行
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 可选配置

### 使用Nginx反向代理

```bash
# nginx.conf 示例
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL证书配置（使用Let's Encrypt）

```bash
# 安装certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 使用环境变量配置LLM（生产环境建议）

创建 `.env` 文件：

```bash
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=your_embedding_key
```

修改 `docker-compose.yml`：

```yaml
services:
  ai-novel-generator:
    # ... 其他配置
    env_file:
      - .env
```

## 技术支持

- 问题反馈：[GitHub Issues](https://github.com/ksbbs/AI_NovelGenerator/issues)
- 分支：`dockerweb`
- 原项目：[AI_NovelGenerator](https://github.com/YILING0013/AI_NovelGenerator)
