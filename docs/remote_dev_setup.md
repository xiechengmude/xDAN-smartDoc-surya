# 远程GPU服务器开发配置指南

## 方案1：SSH端口转发 + 远程开发（推荐）

### 1. SSH配置文件设置
在本地 `~/.ssh/config` 添加：

```bash
Host gpu-server
    HostName your-gpu-server-ip
    User your-username
    Port 22
    # 端口转发：将远程8080映射到本地8080
    LocalForward 8080 localhost:8080
    # 保持连接活跃
    ServerAliveInterval 60
    ServerAliveCountMax 3
    # 压缩传输
    Compression yes
```

### 2. 连接到远程服务器
```bash
# 连接并自动设置端口转发
ssh gpu-server

# 或者直接使用端口转发
ssh -L 8080:localhost:8080 user@gpu-server-ip
```

### 3. 在远程服务器上运行API
```bash
# 在远程服务器上
cd /path/to/xDAN-smartDoc-surya
python pdf_to_markdown_api_simple.py --port 8080 --host 0.0.0.0 --max-concurrent 4
```

### 4. 本地访问
- API服务：http://localhost:8080
- API文档：http://localhost:8080/docs
- 所有请求会通过SSH隧道转发到远程GPU服务器

## 方案2：VS Code Remote Development

### 1. 安装VS Code扩展
- Remote - SSH
- Remote - SSH: Editing Configuration Files

### 2. 配置远程连接
1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Remote-SSH: Connect to Host"
3. 添加远程服务器配置

### 3. 远程开发优势
- 直接在远程服务器编辑代码
- 终端直接运行在远程环境
- 实时查看日志和调试信息
- 文件同步自动处理

## 方案3：tmux + SSH会话管理

### 1. 在远程服务器安装tmux
```bash
# Ubuntu/Debian
sudo apt install tmux

# CentOS/RHEL
sudo yum install tmux
```

### 2. 创建持久会话
```bash
# 连接到远程服务器
ssh user@gpu-server-ip

# 创建新的tmux会话
tmux new-session -d -s surya-api

# 进入会话
tmux attach-session -t surya-api

# 运行API服务
python pdf_to_markdown_api_simple.py --port 8080 --host 0.0.0.0
```

### 3. 会话管理命令
```bash
# 分离会话（服务继续运行）
Ctrl+B, D

# 重新连接会话
tmux attach-session -t surya-api

# 查看所有会话
tmux list-sessions

# 杀死会话
tmux kill-session -t surya-api
```

## 方案4：Docker + 远程部署

### 1. 创建Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "pdf_to_markdown_api_simple.py", "--port", "8080", "--host", "0.0.0.0"]
```

### 2. 远程部署脚本
```bash
#!/bin/bash
# deploy_remote.sh

REMOTE_HOST="user@gpu-server-ip"
REMOTE_PATH="/home/user/surya-api"

# 同步代码到远程服务器
rsync -avz --exclude='.git' --exclude='__pycache__' . $REMOTE_HOST:$REMOTE_PATH/

# 在远程服务器构建和运行
ssh $REMOTE_HOST "cd $REMOTE_PATH && docker build -t surya-api . && docker run -d -p 8080:8080 --gpus all surya-api"
```

## 方案5：Jupyter Notebook远程开发

### 1. 在远程服务器启动Jupyter
```bash
# 远程服务器
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

### 2. 本地端口转发
```bash
# 本地终端
ssh -L 8888:localhost:8888 user@gpu-server-ip
```

### 3. 创建开发Notebook
可以在Jupyter中直接运行和调试API代码，实时查看输出。

## 推荐配置组合

### 最佳实践：VS Code Remote + SSH端口转发
1. 使用VS Code Remote-SSH连接远程服务器
2. 在远程环境中直接编辑和运行代码
3. 设置端口转发访问API服务
4. 使用tmux保持会话持久化

### 快速启动脚本
```bash
#!/bin/bash
# quick_remote_dev.sh

echo "🚀 启动远程GPU开发环境..."

# 检查SSH连接
if ! ssh -q gpu-server exit; then
    echo "❌ 无法连接到远程服务器"
    exit 1
fi

echo "✅ SSH连接正常"

# 同步代码
echo "📁 同步代码到远程服务器..."
rsync -avz --exclude='.git' --exclude='__pycache__' . gpu-server:~/surya-api/

# 启动远程服务
echo "🔥 启动远程API服务..."
ssh gpu-server "cd ~/surya-api && tmux new-session -d -s surya 'python pdf_to_markdown_api_simple.py --port 8080 --host 0.0.0.0 --max-concurrent 4'"

echo "🌐 API服务已启动："
echo "   远程地址: http://gpu-server-ip:8080"
echo "   本地转发: http://localhost:8080 (需要SSH端口转发)"
echo "   API文档: http://localhost:8080/docs"

echo "📱 连接命令："
echo "   ssh -L 8080:localhost:8080 gpu-server"
echo "   tmux attach-session -t surya"
```

这样您就可以：
- 在本地编辑代码
- 在远程GPU服务器运行
- 实时查看终端输出和日志
- 通过端口转发本地访问API
- 保持开发体验的流畅性 