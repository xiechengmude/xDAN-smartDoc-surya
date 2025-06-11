#!/bin/bash

# 一键启动远程开发环境脚本
# 使用方法: ./remote_dev.sh [remote_host] [action]

set -e

# 默认配置
DEFAULT_REMOTE_HOST="pdf_parser"
DEFAULT_REMOTE_PATH="/workspace/pdf_api_service"
DEFAULT_PORT="8090"
DEFAULT_MAX_CONCURRENT="10"

# 获取参数
REMOTE_HOST=${1:-$DEFAULT_REMOTE_HOST}
ACTION=${2:-"start"}

echo "🚀 远程GPU开发环境管理"
echo "   服务器: $REMOTE_HOST"
echo "   操作: $ACTION"

# 检查SSH连接
check_connection() {
    echo "🔍 检查SSH连接..."
    if ! ssh -q -o ConnectTimeout=5 $REMOTE_HOST exit; then
        echo "❌ 无法连接到远程服务器 $REMOTE_HOST"
        echo "请检查SSH配置和网络连接"
        exit 1
    fi
    echo "✅ SSH连接正常"
}

# 同步代码
sync_code() {
    echo "📤 同步代码到远程服务器..."
    ./scripts/sync_to_remote.sh $REMOTE_HOST $DEFAULT_REMOTE_PATH
}

# 启动服务
start_service() {
    echo "🔥 启动远程API服务..."
    
    # 检查并停止占用端口的进程
    echo "🔍 检查端口 $DEFAULT_PORT 占用情况..."
    ssh $REMOTE_HOST "
        # 查找占用端口的进程
        PORT_PID=\$(lsof -ti:$DEFAULT_PORT 2>/dev/null || true)
        if [ ! -z \"\$PORT_PID\" ]; then
            echo \"⚠️  端口 $DEFAULT_PORT 被进程 \$PORT_PID 占用，正在终止...\"
            kill -9 \$PORT_PID 2>/dev/null || true
            sleep 2
        fi
        
        # 停止已有的tmux会话
        if tmux has-session -t surya-api 2>/dev/null; then
            echo \"⚠️  停止已有的tmux会话...\"
            tmux kill-session -t surya-api 2>/dev/null || true
            sleep 2
        fi
        
        # 再次检查端口是否释放
        if lsof -ti:$DEFAULT_PORT 2>/dev/null; then
            echo \"❌ 端口 $DEFAULT_PORT 仍被占用，请手动检查\"
            exit 1
        fi
    "
    
    # 启动新的tmux会话（使用uv环境）
    ssh $REMOTE_HOST "cd $DEFAULT_REMOTE_PATH && tmux new-session -d -s surya-api 'source ~/.local/bin/env && uv run python pdf_to_markdown_api_simple.py --port $DEFAULT_PORT --host 0.0.0.0 --max-concurrent $DEFAULT_MAX_CONCURRENT'"
    
    sleep 3
    
    # 检查服务状态
    if ssh $REMOTE_HOST "tmux has-session -t surya-api 2>/dev/null"; then
        echo "✅ API服务启动成功"
        
        # 获取远程服务器IP
        REMOTE_IP=$(ssh $REMOTE_HOST "hostname -I | awk '{print \$1}'")
        
        echo ""
        echo "🌐 服务访问信息："
        echo "   远程直接访问: http://$REMOTE_IP:$DEFAULT_PORT"
        echo "   API文档: http://$REMOTE_IP:$DEFAULT_PORT/docs"
        echo ""
        echo "🔗 本地端口转发访问："
        echo "   1. 新开终端执行: ssh -L $DEFAULT_PORT:localhost:$DEFAULT_PORT $REMOTE_HOST"
        echo "   2. 访问: http://localhost:$DEFAULT_PORT"
        echo "   3. API文档: http://localhost:$DEFAULT_PORT/docs"
        echo ""
        echo "📱 管理命令："
        echo "   查看日志: ssh $REMOTE_HOST 'tmux attach-session -t surya-api'"
        echo "   停止服务: ./remote_dev.sh $REMOTE_HOST stop"
        echo "   重启服务: ./remote_dev.sh $REMOTE_HOST restart"
        
    else
        echo "❌ API服务启动失败"
        echo "请检查远程服务器的Python环境和依赖"
        exit 1
    fi
}

# 停止服务
stop_service() {
    echo "🛑 停止远程API服务..."
    if ssh $REMOTE_HOST "tmux has-session -t surya-api 2>/dev/null"; then
        ssh $REMOTE_HOST "tmux kill-session -t surya-api"
        echo "✅ 服务已停止"
    else
        echo "ℹ️  没有运行的服务"
    fi
}

# 查看服务状态
status_service() {
    echo "📊 检查服务状态..."
    if ssh $REMOTE_HOST "tmux has-session -t surya-api 2>/dev/null"; then
        echo "✅ 服务正在运行"
        
        # 尝试获取服务信息
        REMOTE_IP=$(ssh $REMOTE_HOST "hostname -I | awk '{print \$1}'")
        echo "   访问地址: http://$REMOTE_IP:$DEFAULT_PORT"
        
        # 检查端口是否监听
        if ssh $REMOTE_HOST "netstat -tlnp 2>/dev/null | grep :$DEFAULT_PORT" >/dev/null; then
            echo "   端口状态: ✅ 监听中"
        else
            echo "   端口状态: ⚠️  未监听"
        fi
        
        echo ""
        echo "📱 管理命令："
        echo "   查看日志: ssh $REMOTE_HOST 'tmux attach-session -t surya-api'"
        echo "   分离会话: Ctrl+B, D"
        
    else
        echo "❌ 服务未运行"
    fi
}

# 查看日志
logs_service() {
    echo "📋 连接到服务日志..."
    echo "提示: 按 Ctrl+B, D 分离会话但保持服务运行"
    ssh -t $REMOTE_HOST "tmux attach-session -t surya-api"
}

# 重启服务
restart_service() {
    echo "🔄 重启远程API服务..."
    stop_service
    sleep 2
    sync_code
    start_service
}

# 安装依赖
install_deps() {
    echo "📦 在远程服务器安装依赖..."
    ssh $REMOTE_HOST "cd $DEFAULT_REMOTE_PATH && source ~/.local/bin/env && uv sync"
    echo "✅ 依赖安装完成"
}

# 主逻辑
case $ACTION in
    "start")
        check_connection
        sync_code
        start_service
        ;;
    "stop")
        check_connection
        stop_service
        ;;
    "restart")
        check_connection
        restart_service
        ;;
    "status")
        check_connection
        status_service
        ;;
    "logs")
        check_connection
        logs_service
        ;;
    "sync")
        check_connection
        sync_code
        ;;
    "install")
        check_connection
        install_deps
        ;;
    *)
        echo "使用方法: $0 [remote_host] [action]"
        echo ""
        echo "可用操作:"
        echo "  start   - 同步代码并启动服务 (默认)"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看服务日志"
        echo "  sync    - 仅同步代码"
        echo "  install - 安装依赖"
        echo ""
        echo "示例:"
        echo "  $0                          # 使用默认服务器启动"
        echo "  $0 my-gpu-server start      # 指定服务器启动"
        echo "  $0 my-gpu-server status     # 查看状态"
        exit 1
        ;;
esac 