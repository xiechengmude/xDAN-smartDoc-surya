#!/bin/bash

# xDAN Smart API 停止脚本
echo "🛑 停止 xDAN Smart API..."

# 查找并停止所有相关进程
PIDS=$(ps aux | grep pdf_to_markdown_api.py | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "ℹ️  没有找到运行中的 API 服务"
else
    echo "🔍 找到运行中的进程: $PIDS"
    
    # 优雅停止
    echo "📤 发送 TERM 信号..."
    kill $PIDS 2>/dev/null
    
    # 等待进程停止
    sleep 3
    
    # 检查是否还有进程在运行
    REMAINING=$(ps aux | grep pdf_to_markdown_api.py | grep -v grep | awk '{print $2}')
    
    if [ ! -z "$REMAINING" ]; then
        echo "⚡ 强制停止剩余进程: $REMAINING"
        kill -9 $REMAINING 2>/dev/null
        sleep 1
    fi
    
    # 最终检查
    FINAL_CHECK=$(ps aux | grep pdf_to_markdown_api.py | grep -v grep)
    
    if [ -z "$FINAL_CHECK" ]; then
        echo "✅ 所有 API 服务已成功停止"
    else
        echo "❌ 仍有进程在运行:"
        echo "$FINAL_CHECK"
    fi
fi

# 检查端口占用
PORT_CHECK=$(netstat -tlnp 2>/dev/null | grep :8000 || ss -tlnp 2>/dev/null | grep :8000)
if [ ! -z "$PORT_CHECK" ]; then
    echo "⚠️  端口 8000 仍被占用:"
    echo "$PORT_CHECK"
else
    echo "✅ 端口 8000 已释放"
fi 