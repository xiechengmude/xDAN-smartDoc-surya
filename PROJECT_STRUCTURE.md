# xDAN Smart Doc Surya - 项目结构

## 📁 项目目录结构

```
xDAN-smartDoc-surya/
├── main.py                          # 🚀 主入口文件 (优化版API)
├── api/                             # 📡 API实现目录
│   ├── pdf_to_markdown_api.py       # 🎯 优化版PDF转Markdown API (主版本)
│   └── surya_config.py              # ⚡ Surya性能优化配置
├── scripts/                         # 🛠️ 管理脚本
│   ├── remote_dev.sh                # 🌐 远程开发环境管理
│   ├── local_tunnel.sh              # 🔗 SSH端口转发管理
│   ├── sync_to_remote.sh            # 📤 代码同步到远程
│   └── test_remote_api.py           # 🧪 远程API测试脚本
├── tests/                           # 🧪 测试目录
├── docs/                            # 📚 文档目录
│   └── DEPLOYMENT_GUIDE.md          # 📖 部署指南
├── surya/                           # 🔍 Surya OCR核心模块
├── requirements.txt                 # 📦 Python依赖
├── pyproject.toml                   # 🔧 uv项目配置
├── setup_remote_dev.sh              # 🚀 一键远程环境配置
└── test_pdf_urls.md                 # 📄 测试PDF URL列表
```

## 🎯 核心文件说明

### 主要API文件
- **`api/pdf_to_markdown_api.py`** - 优化版PDF转Markdown API
  - 支持页面范围选择 (`page_range`)
  - 高性能批处理优化
  - 智能并发控制
  - 完整的API密钥管理

### 性能优化
- **`api/surya_config.py`** - Surya性能优化配置
  - 自动硬件检测和配置
  - 批处理大小优化
  - 编译加速设置
  - 并发工作者优化

### 部署和管理
- **`main.py`** - 统一入口，直接启动优化版API
- **`setup_remote_dev.sh`** - 一键配置远程GPU环境
- **`scripts/remote_dev.sh`** - 远程服务管理 (启动/停止/重启/日志)
- **`scripts/local_tunnel.sh`** - SSH端口转发管理

## 🚀 快速启动

### 本地启动 (如果支持)
```bash
python main.py --port 8080 --max-concurrent 3
```

### 远程GPU启动
```bash
# 配置远程环境
./setup_remote_dev.sh

# 启动远程服务
./scripts/remote_dev.sh pdf_parser start

# 建立端口转发
./scripts/local_tunnel.sh pdf_parser 8080 8080
```

## 📈 性能特性

- **智能批处理**: 根据硬件自动调整批处理大小
- **编译优化**: GPU环境下自动启用模型编译加速
- **并发控制**: 智能并发任务管理，避免资源竞争
- **页面范围**: 支持灵活的页面选择 (`"0,5-10,20"`)
- **硬件适配**: 自动检测并优化MPS/CUDA/CPU配置
