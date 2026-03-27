# AI小说生成器 - Docker 部署指南

## 快速部署

### 方式一：使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/YILING0013/AI_NovelGenerator
cd AI_NovelGenerator

# 2. 修改密码（重要！）
# 编辑 docker-compose.yml 中的 APP_USERNAME 和 APP_PASSWORD

# 3. 启动服务
docker-compose up -d

# 4. 访问服务
# 打开浏览器访问 http://localhost:7860
```

### 方式二：使用 Docker 命令

```bash
# 1. 构建镜像
docker build -t ai-novel-generator .

# 2. 运行容器
docker run -d \
  --name novel-generator \
  -p 7860:7860 \
  -e APP_USERNAME=admin \
  -e APP_PASSWORD=your_secure_password \
  -v $(pwd)/novels:/app/novels \
  -v $(pwd)/config.json:/app/config.json \
  ai-novel-generator

# 3. 访问服务
# 打开浏览器访问 http://localhost:7860
```

### 方式四：本地运行（Windows）

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install gradio

# 2. 运行启动脚本
start.bat

# 或者直接运行
python web_app.py
```

### 方式五：本地运行（Linux/Mac）

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install gradio

# 2. 赋予执行权限
chmod +x start.sh

# 3. 运行启动脚本
./start.sh
```

### 方式六：Zeabur 一键部署（推荐公网部署）

[![Deploy on Zeabur](https://zeabur.com/button.svg)](https://zeabur.com/templates/xxxxx)

#### 步骤 1: 在 Zeabur 创建服务

1. 登录 [Zeabur](https://zeabur.com)
2. 创建新项目
3. 添加服务 → 选择 **Docker**
4. 镜像地址填写: `ghcr.io/ksbbs/ai_novelgenerator:latest`

#### 步骤 2: 配置环境变量

在 Zeabur 控制台 → 服务 → 环境变量 中添加：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `APP_USERNAME` | `admin` | 登录用户名 |
| `APP_PASSWORD` | `你的强密码` | **必须修改** |
| `TZ` | `Asia/Shanghai` | 时区 |

#### 步骤 3: 配置持久化存储

在 Zeabur 控制台 → 服务 → 存储 中添加：

| 挂载路径 | 说明 |
|----------|------|
| `/app/novels` | 生成的小说文件 |
| `/app/vectorstore` | 向量数据库 |

#### 步骤 4: 配置端口

在 Zeabur 控制台 → 服务 → 网络：
- 端口: `7860`
- 开启 **公开访问**

#### 步骤 5: 绑定域名（可选）

在 Zeabur 控制台 → 服务 → 域名：
- 添加自定义域名或使用 Zeabur 提供的域名

#### Zeabur 配置示例图

```
┌─────────────────────────────────────────┐
│  环境变量                                │
├─────────────────────────────────────────┤
│  APP_USERNAME = admin                   │
│  APP_PASSWORD = your_strong_password    │
│  TZ = Asia/Shanghai                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  持久化存储                              │
├─────────────────────────────────────────┤
│  /app/novels      → 1GB                 │
│  /app/vectorstore → 1GB                 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  网络                                    │
├─────────────────────────────────────────┤
│  端口: 7860                              │
│  公开访问: ✅                            │
│  域名: novel.your-domain.com            │
└─────────────────────────────────────────┘
```

## 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| APP_USERNAME | 登录用户名 | admin |
| APP_PASSWORD | 登录密码 | novel2024 |
| TZ | 时区 | Asia/Shanghai |

## 公网部署建议

### 1. 安全配置

```yaml
# docker-compose.yml 中修改
environment:
  - APP_USERNAME=your_username
  - APP_PASSWORD=your_strong_password_here
```

### 2. 反向代理配置（Nginx示例）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 强制HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. 使用 Docker 部署到云服务器

```bash
# 上传项目到服务器
scp -r AI_NovelGenerator user@server:/home/user/

# SSH 登录服务器
ssh user@server

# 进入项目目录
cd /home/user/AI_NovelGenerator

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 更新部署
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 数据持久化

以下目录需要持久化存储：
- `novels/` - 生成的小说文件
- `vectorstore/` - 向量数据库
- `config.json` - 配置文件

## 故障排查

### 1. 无法访问服务
```bash
# 检查容器状态
docker-compose ps

# 检查端口占用
netstat -tlnp | grep 7860
```

### 2. 登录失败
```bash
# 查看环境变量
docker-compose exec novel-generator env | grep APP
```

### 3. 配置问题
```bash
# 检查配置文件
cat config.json
```

## 端口说明

| 端口 | 用途 |
|------|------|
| 7860 | Web服务端口（Gradio） |

---

**安全提醒**：部署到公网前，请务必修改默认密码！
