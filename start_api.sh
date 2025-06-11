#!/bin/bash

# xDAN Smart API 快速启动脚本
echo "🚀 启动 xDAN Smart API..."

# 检查是否在正确的目录
if [ ! -f "pdf_to_markdown_api.py" ]; then
    echo "❌ 错误: 找不到 pdf_to_markdown_api.py 文件"
    echo "请确保在项目根目录下运行此脚本"
    exit 1
fi

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin dev

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ 错误: 找不到 Python"
    exit 1
fi

# 停止已存在的服务
echo "🛑 停止已存在的服务..."
pkill -f pdf_to_markdown_api.py 2>/dev/null || true

# 等待进程完全停止
sleep 2

# 启动新服务
echo "🌐 启动 API 服务..."
nohup python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000 > api.log 2>&1 &

# 获取进程ID
PID=$!
echo "✅ API 已启动，进程ID: $PID"

# 等待几秒让服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务是否正在运行
if ps -p $PID > /dev/null; then
    echo "🎉 服务启动成功！"
    echo "📊 服务地址: http://0.0.0.0:8000"
    echo "📖 API文档: http://0.0.0.0:8000/docs"
    echo "📝 查看日志: tail -f api.log"
    echo "🔍 检查进程: ps aux | grep pdf_to_markdown_api"
    echo "🛑 停止服务: pkill -f pdf_to_markdown_api"
else
    echo "❌ 服务启动失败，请检查日志:"
    tail -20 api.log
    exit 1
fi 