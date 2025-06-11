#!/bin/bash

# 一键配置远程开发环境脚本
# 使用方法: ./setup_remote_dev.sh

set -e

echo "🚀 配置远程GPU开发环境"
echo "   目标服务器: pdf_parser (root@159.54.182.15)"
echo "   项目路径: /workspace/pdf_api_service"
echo "   端口: 8090"
echo "   环境管理: uv"
echo ""

# 检查SSH配置
echo "🔍 检查SSH配置..."
SSH_CONFIG_FILE="$HOME/.ssh/config"

if [ ! -f "$SSH_CONFIG_FILE" ]; then
    echo "📝 创建SSH配置文件..."
    mkdir -p ~/.ssh
    touch "$SSH_CONFIG_FILE"
    chmod 600 "$SSH_CONFIG_FILE"
fi

# 检查是否已有pdf_parser配置
if grep -q "Host pdf_parser" "$SSH_CONFIG_FILE"; then
    echo "✅ SSH配置中已存在pdf_parser配置"
else
    echo "📝 添加pdf_parser SSH配置..."
    cat >> "$SSH_CONFIG_FILE" << 'EOF'

# Surya API远程开发服务器
Host pdf_parser
    HostName 159.54.182.15
    User root
    Port 22
    # 端口转发：将远程8090映射到本地8090
    LocalForward 8090 localhost:8090
    # 保持连接活跃
    ServerAliveInterval 60
    ServerAliveCountMax 3
    # 压缩传输
    Compression yes
EOF
    echo "✅ SSH配置已添加"
fi

# 测试SSH连接
echo "🔍 测试SSH连接..."
if ssh -q -o ConnectTimeout=10 -o BatchMode=yes pdf_parser exit 2>/dev/null; then
    echo "✅ SSH连接测试成功"
else
    echo "⚠️  SSH连接测试失败"
    echo ""
    echo "可能的原因："
    echo "1. 服务器地址不正确"
    echo "2. 需要配置SSH密钥认证"
    echo "3. 需要输入密码"
    echo ""
    echo "请手动测试连接: ssh pdf_parser"
    echo "如果需要密码，请确保可以正常登录"
    echo ""
    read -p "是否继续配置? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 配置已取消"
        exit 1
    fi
fi

# 检查远程服务器Python环境
echo "🐍 检查远程Python环境..."
if ssh pdf_parser "python3 --version" 2>/dev/null; then
    PYTHON_VERSION=$(ssh pdf_parser "python3 --version 2>&1")
    echo "   远程Python版本: $PYTHON_VERSION"
    
    # 检查Python版本是否支持
    PYTHON_MAJOR=$(ssh pdf_parser "python3 -c 'import sys; print(sys.version_info.major)'")
    PYTHON_MINOR=$(ssh pdf_parser "python3 -c 'import sys; print(sys.version_info.minor)'")
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo "✅ Python版本支持 (3.10+)"
    else
        echo "⚠️  Python版本较低 ($PYTHON_MAJOR.$PYTHON_MINOR)，建议使用Python 3.10+"
        echo "   Surya项目使用了Python 3.10+的新语法特性"
    fi
else
    echo "❌ 远程服务器Python环境检查失败"
    echo "请确保远程服务器已安装Python 3.10+"
fi

# 检查uv环境
echo "📦 检查uv环境..."
if ssh pdf_parser "command -v uv || test -f ~/.local/bin/uv" 2>/dev/null; then
    UV_VERSION=$(ssh pdf_parser "~/.local/bin/uv --version 2>/dev/null || uv --version 2>/dev/null")
    echo "✅ uv已安装: $UV_VERSION"
else
    echo "⚠️  uv未安装，正在安装..."
    if ssh pdf_parser "curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env" 2>/dev/null; then
        echo "✅ uv安装成功"
        # 验证安装
        if ssh pdf_parser "~/.local/bin/uv --version" 2>/dev/null; then
            UV_VERSION=$(ssh pdf_parser "~/.local/bin/uv --version")
            echo "   版本: $UV_VERSION"
        else
            echo "⚠️  uv安装可能有问题，请手动验证"
        fi
    else
        echo "❌ uv安装失败，请手动安装"
        echo "   安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "   然后运行: source ~/.local/bin/env"
    fi
fi

# 检查GPU环境
echo "🎮 检查GPU环境..."
if ssh pdf_parser "nvidia-smi" 2>/dev/null; then
    echo "✅ 检测到NVIDIA GPU"
    GPU_INFO=$(ssh pdf_parser "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits" | head -1)
    echo "   GPU信息: $GPU_INFO"
else
    echo "⚠️  未检测到NVIDIA GPU或nvidia-smi不可用"
    echo "   将使用CPU模式运行"
fi

echo ""
echo "🎉 远程开发环境配置完成！"
echo ""
echo "📱 下一步操作："
echo ""
echo "1. 🚀 启动远程服务:"
echo "   ./scripts/remote_dev.sh start"
echo ""
echo "2. 🔗 建立端口转发 (新终端窗口):"
echo "   ./scripts/local_tunnel.sh"
echo "   或者: ssh pdf_parser"
echo ""
echo "3. 🌐 访问API服务:"
echo "   http://localhost:8090"
echo "   http://localhost:8090/docs"
echo ""
echo "4. 📊 管理服务:"
echo "   ./scripts/remote_dev.sh status   # 查看状态"
echo "   ./scripts/remote_dev.sh logs     # 查看日志"
echo "   ./scripts/remote_dev.sh stop     # 停止服务"
echo ""
echo "💡 提示:"
echo "   - 所有脚本都已配置为使用pdf_parser服务器"
echo "   - 代码修改后使用 ./scripts/remote_dev.sh restart 重启服务"
echo "   - 使用tmux会话管理，服务在后台持续运行" 