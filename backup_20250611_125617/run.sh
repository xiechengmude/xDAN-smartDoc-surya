#!/bin/bash

# xDAN Smart API 快速启动脚本

echo "🚀 xDAN Smart API 快速启动"
echo "=========================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    exit 1
fi

# 检查必要文件
if [ ! -f "pdf_to_markdown_api.py" ]; then
    echo "❌ 未找到pdf_to_markdown_api.py文件"
    exit 1
fi

# 设置默认参数
PORT=${PORT:-8080}
HOST=${HOST:-127.0.0.1}
MAX_CONCURRENT=${MAX_CONCURRENT:-5}
AUTO_OPTIMIZE=${AUTO_OPTIMIZE:-true}

echo "📋 启动配置:"
echo "   端口: $PORT"
echo "   主机: $HOST"
echo "   最大并发: $MAX_CONCURRENT"
echo "   自动优化: $AUTO_OPTIMIZE"
echo ""

# 检查性能配置
if [ "$AUTO_OPTIMIZE" = "true" ] && [ -f "surya_config.py" ]; then
    echo "🔧 运行性能分析..."
    python3 surya_config.py
    echo ""
fi

# 启动API服务
if [ -f "start_optimized_api.py" ]; then
    echo "🚀 使用优化启动脚本..."
    if [ "$AUTO_OPTIMIZE" = "true" ]; then
        python3 start_optimized_api.py --port $PORT --host $HOST --max-concurrent $MAX_CONCURRENT --auto-optimize
    else
        python3 start_optimized_api.py --port $PORT --host $HOST --max-concurrent $MAX_CONCURRENT
    fi
else
    echo "🚀 使用标准启动方式..."
    python3 pdf_to_markdown_api.py --port $PORT --host $HOST --max-concurrent $MAX_CONCURRENT
fi 