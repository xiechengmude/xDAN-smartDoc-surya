# 远程GPU开发环境使用指南

## 概述

本指南帮助您在本地开发，但在远程GPU服务器上运行Surya OCR API服务。通过SSH端口转发，您可以：
- 在本地编辑代码
- 在远程GPU服务器运行服务
- 通过本地端口访问远程API
- 实时查看远程服务日志

## 服务器信息

- **主机名**: pdf_parser
- **用户**: root
- **端口**: 22 (SSH), 8080 (API)

## 快速开始

### 1. 一键配置环境

```bash
./setup_remote_dev.sh
```

这个脚本会：
- 自动配置SSH连接
- 测试远程服务器连接
- 检查Python和GPU环境
- 提供后续操作指导

### 2. 启动远程服务

```bash
./scripts/remote_dev.sh start
```

这会：
- 同步本地代码到远程服务器
- 在远程服务器启动API服务
- 使用tmux会话管理服务

### 3. 建立端口转发

**新开一个终端窗口**，运行：

```bash
./scripts/local_tunnel.sh
```

或者直接使用SSH：

```bash
ssh pdf_parser
```

### 4. 访问API服务

- **API服务**: http://localhost:8080
- **API文档**: http://localhost:8080/docs
- **健康检查**: http://localhost:8080/health

### 5. 测试API功能

```bash
python scripts/test_remote_api.py
```

## 详细操作指南

### SSH配置

脚本会自动在 `~/.ssh/config` 中添加以下配置：

```
Host pdf_parser
    HostName pdf_parser
    User root
    Port 22
    LocalForward 8080 localhost:8080
    ServerAliveInterval 60
    ServerAliveCountMax 3
    Compression yes
```

### 服务管理命令

```bash
# 启动服务（同步代码 + 启动）
./scripts/remote_dev.sh start

# 查看服务状态
./scripts/remote_dev.sh status

# 查看服务日志（进入tmux会话）
./scripts/remote_dev.sh logs

# 停止服务
./scripts/remote_dev.sh stop

# 重启服务（停止 + 同步 + 启动）
./scripts/remote_dev.sh restart

# 仅同步代码
./scripts/remote_dev.sh sync

# 安装依赖
./scripts/remote_dev.sh install
```

### 端口转发管理

```bash
# 启动端口转发（自动重连）
./scripts/local_tunnel.sh

# 指定不同端口
./scripts/local_tunnel.sh pdf_parser 8081 8080
```

### 代码同步

```bash
# 手动同步代码
./scripts/sync_to_remote.sh

# 指定不同路径
./scripts/sync_to_remote.sh pdf_parser ~/my-surya-api
```

## 开发工作流

### 典型开发流程

1. **本地编辑代码**
   - 使用您喜欢的编辑器修改代码
   - 所有修改都在本地进行

2. **同步并重启服务**
   ```bash
   ./scripts/remote_dev.sh restart
   ```

3. **测试API功能**
   ```bash
   python scripts/test_remote_api.py
   ```

4. **查看日志调试**
   ```bash
   ./scripts/remote_dev.sh logs
   # 按 Ctrl+B, D 分离会话但保持服务运行
   ```

### 快速调试

```bash
# 一键重启并查看日志
./scripts/remote_dev.sh restart && ./scripts/remote_dev.sh logs
```

### 多终端工作

建议开启3个终端窗口：

1. **主开发终端**: 编辑代码，运行管理命令
2. **端口转发终端**: 运行 `./scripts/local_tunnel.sh`
3. **日志监控终端**: 运行 `./scripts/remote_dev.sh logs`

## 故障排除

### SSH连接问题

```bash
# 测试SSH连接
ssh pdf_parser

# 如果需要密码认证，确保可以正常登录
# 如果使用密钥认证，检查密钥配置
```

### 端口转发问题

```bash
# 检查本地端口占用
lsof -i :8080

# 检查远程服务状态
./scripts/remote_dev.sh status

# 重新建立端口转发
./scripts/local_tunnel.sh
```

### 服务启动问题

```bash
# 查看详细错误信息
./scripts/remote_dev.sh logs

# 检查远程Python环境
ssh pdf_parser "python3 --version"

# 检查依赖安装
./scripts/remote_dev.sh install
```

### Python版本兼容性

如果遇到类型注解错误（如 `unsupported operand type(s) for |`），说明远程服务器Python版本低于3.10。

**解决方案**：
1. 升级远程服务器Python到3.10+
2. 或者使用兼容版本的代码

## 性能优化

### GPU配置

脚本会自动检测GPU并优化配置：
- 自动调整批处理大小
- 启用GPU加速
- 优化内存使用

### 并发设置

```bash
# 调整最大并发数
./scripts/remote_dev.sh start
# 默认并发数为4，可在脚本中修改
```

## 安全注意事项

1. **SSH密钥**: 建议使用SSH密钥而非密码认证
2. **防火墙**: 确保8080端口仅对内网开放
3. **权限**: 使用最小必要权限原则

## 高级配置

### 自定义配置

编辑脚本中的默认配置：

```bash
# scripts/remote_dev.sh
DEFAULT_REMOTE_HOST="pdf_parser"
DEFAULT_REMOTE_PATH="~/surya-api"
DEFAULT_PORT="8080"
DEFAULT_MAX_CONCURRENT="4"
```

### VS Code Remote开发

1. 安装VS Code Remote-SSH扩展
2. 连接到pdf_parser
3. 直接在远程环境编辑代码

### Docker部署

如果远程服务器支持Docker：

```bash
# 在远程服务器构建镜像
ssh pdf_parser "cd ~/surya-api && docker build -t surya-api ."

# 运行容器
ssh pdf_parser "docker run -d -p 8080:8080 --gpus all surya-api"
```

## 常用命令速查

```bash
# 环境配置
./setup_remote_dev.sh

# 服务管理
./scripts/remote_dev.sh start|stop|restart|status|logs

# 端口转发
./scripts/local_tunnel.sh

# 代码同步
./scripts/sync_to_remote.sh

# API测试
python scripts/test_remote_api.py

# 直接SSH连接
ssh pdf_parser
```

## 支持

如果遇到问题，请检查：
1. SSH连接是否正常
2. 远程服务器Python环境
3. GPU驱动和CUDA环境
4. 网络连接和防火墙设置 