#!/bin/bash

# 远程服务器代码同步脚本
# 使用方法: ./sync_to_remote.sh [remote_host] [remote_path]

set -e

# 默认配置
DEFAULT_REMOTE_HOST="pdf_parser"
DEFAULT_REMOTE_PATH="/workspace/pdf_api_service"

# 获取参数
REMOTE_HOST=${1:-$DEFAULT_REMOTE_HOST}
REMOTE_PATH=${2:-$DEFAULT_REMOTE_PATH}

echo "🚀 同步代码到远程GPU服务器..."
echo "   目标服务器: $REMOTE_HOST"
echo "   目标路径: $REMOTE_PATH"

# 检查SSH连接
echo "🔍 检查SSH连接..."
if ! ssh -q -o ConnectTimeout=5 $REMOTE_HOST exit; then
    echo "❌ 无法连接到远程服务器 $REMOTE_HOST"
    echo "请检查："
    echo "  1. 服务器地址是否正确"
    echo "  2. SSH密钥是否配置"
    echo "  3. 网络连接是否正常"
    exit 1
fi
echo "✅ SSH连接正常"

# 创建远程目录
echo "📁 创建远程目录..."
ssh $REMOTE_HOST "mkdir -p $REMOTE_PATH"

# 同步代码
echo "📤 同步代码文件..."
rsync -avz --progress \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.env' \
    --exclude='logs' \
    --exclude='temp' \
    . $REMOTE_HOST:$REMOTE_PATH/

echo "✅ 代码同步完成"

# 检查远程Python环境
echo "🐍 检查远程Python环境..."
PYTHON_VERSION=$(ssh $REMOTE_HOST "cd $REMOTE_PATH && python --version 2>&1" || echo "Python not found")
echo "   远程Python版本: $PYTHON_VERSION"

# 检查依赖
echo "📦 检查依赖安装..."
if ssh $REMOTE_HOST "cd $REMOTE_PATH && python -c 'import torch; print(f\"PyTorch: {torch.__version__}\")'" 2>/dev/null; then
    echo "✅ PyTorch已安装"
else
    echo "⚠️  PyTorch未安装，请在远程服务器安装依赖"
fi

if ssh $REMOTE_HOST "cd $REMOTE_PATH && python -c 'import fastapi; print(f\"FastAPI: {fastapi.__version__}\")'" 2>/dev/null; then
    echo "✅ FastAPI已安装"
else
    echo "⚠️  FastAPI未安装，请在远程服务器安装依赖"
fi

echo ""
echo "🎉 同步完成！"
echo ""
echo "📱 下一步操作："
echo "   1. 连接到远程服务器: ssh $REMOTE_HOST"
echo "   2. 进入项目目录: cd $REMOTE_PATH"
echo "   3. 启动API服务: python pdf_to_markdown_api_simple.py --port 8080 --host 0.0.0.0"
echo ""
echo "🌐 本地访问（需要端口转发）:"
echo "   ssh -L 8080:localhost:8080 $REMOTE_HOST"
echo "   然后访问: http://localhost:8080" 