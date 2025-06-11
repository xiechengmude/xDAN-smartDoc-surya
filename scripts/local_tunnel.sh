#!/bin/bash

# 本地端口转发脚本
# 使用方法: ./local_tunnel.sh [remote_host] [local_port] [remote_port]

set -e

# 默认配置
DEFAULT_REMOTE_HOST="pdf_parser"
DEFAULT_LOCAL_PORT="8090"
DEFAULT_REMOTE_PORT="8090"

# 获取参数
REMOTE_HOST=${1:-$DEFAULT_REMOTE_HOST}
LOCAL_PORT=${2:-$DEFAULT_LOCAL_PORT}
REMOTE_PORT=${3:-$DEFAULT_REMOTE_PORT}

echo "🔗 启动SSH端口转发隧道"
echo "   远程服务器: $REMOTE_HOST"
echo "   本地端口: $LOCAL_PORT"
echo "   远程端口: $REMOTE_PORT"

# 检查本地端口是否被占用
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  本地端口 $LOCAL_PORT 已被占用"
    echo "正在使用该端口的进程:"
    lsof -Pi :$LOCAL_PORT -sTCP:LISTEN
    echo ""
    read -p "是否要杀死占用进程并继续? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔪 杀死占用进程..."
        lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t | xargs kill -9
        sleep 2
    else
        echo "❌ 取消操作"
        exit 1
    fi
fi

# 检查SSH连接
echo "🔍 检查SSH连接..."
if ! ssh -q -o ConnectTimeout=5 $REMOTE_HOST exit; then
    echo "❌ 无法连接到远程服务器 $REMOTE_HOST"
    echo "请检查SSH配置和网络连接"
    exit 1
fi
echo "✅ SSH连接正常"

# 检查远程端口是否监听
echo "🔍 检查远程服务状态..."
if ssh $REMOTE_HOST "netstat -tlnp 2>/dev/null | grep :$REMOTE_PORT" >/dev/null; then
    echo "✅ 远程端口 $REMOTE_PORT 正在监听"
else
    echo "⚠️  远程端口 $REMOTE_PORT 未监听"
    echo "请确保远程服务已启动"
    echo "可以使用: ./remote_dev.sh $REMOTE_HOST start"
    read -p "是否继续建立隧道? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 取消操作"
        exit 1
    fi
fi

echo ""
echo "🚀 启动端口转发隧道..."
echo "   本地访问地址: http://localhost:$LOCAL_PORT"
echo "   API文档: http://localhost:$LOCAL_PORT/docs"
echo ""
echo "💡 提示:"
echo "   - 保持此终端窗口打开以维持隧道连接"
echo "   - 按 Ctrl+C 停止端口转发"
echo "   - 如果连接断开，脚本会自动重连"
echo ""

# 启动端口转发，带自动重连
while true; do
    echo "🔗 建立SSH隧道连接..."
    
    # 使用SSH端口转发，带保活设置
    ssh -L $LOCAL_PORT:localhost:$REMOTE_PORT \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -N $REMOTE_HOST
    
    # 如果SSH退出，检查是否是用户主动退出
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 130 ]; then
        # Ctrl+C 退出
        echo ""
        echo "👋 用户主动退出端口转发"
        break
    else
        # 连接断开，尝试重连
        echo "⚠️  SSH连接断开 (退出码: $EXIT_CODE)"
        echo "🔄 5秒后尝试重新连接..."
        sleep 5
        
        # 检查远程服务器是否可达
        if ! ssh -q -o ConnectTimeout=5 $REMOTE_HOST exit; then
            echo "❌ 无法连接到远程服务器，停止重连"
            break
        fi
    fi
done

echo "✅ 端口转发已停止" 