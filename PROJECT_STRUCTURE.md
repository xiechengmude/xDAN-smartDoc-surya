# 项目结构说明

## 目录结构

```
xDAN-smartDoc-surya/
├── main.py                 # 主API入口文件
├── pyproject.toml         # uv项目配置
├── requirements.txt       # 依赖列表
├── setup_remote_dev.sh    # 远程环境配置脚本
├── test_pdf_urls.md      # 测试PDF列表
├── api/                  # API相关文件
│   ├── pdf_to_markdown_api_simple.py  # 主API实现
│   ├── pdf_to_markdown_api.py         # 完整版API
│   ├── pdf_to_markdown_api_native.py  # 原生版API
│   └── surya_config.py               # Surya配置
├── scripts/              # 部署和管理脚本
│   ├── remote_dev.sh     # 远程服务管理
│   ├── local_tunnel.sh   # 本地端口转发
│   ├── sync_to_remote.sh # 代码同步
│   └── test_remote_api.py # API测试
├── tests/                # 测试文件
│   └── test_single_pdf.py
├── docs/                 # 文档文件
│   ├── README_remote_dev.md
│   ├── PDF_API_文档.md
│   └── ...
├── surya/                # Surya OCR核心代码
└── benchmark/            # 基准测试
```

## 主要文件说明

### 核心文件
- `main.py`: 主API入口，调用api/pdf_to_markdown_api_simple.py
- `pyproject.toml`: uv项目配置，包含所有依赖
- `setup_remote_dev.sh`: 一键配置远程开发环境

### API文件 (api/)
- `pdf_to_markdown_api_simple.py`: 推荐使用的简化版API
- `pdf_to_markdown_api.py`: 功能完整的API版本
- `pdf_to_markdown_api_native.py`: 使用Surya原生功能的版本
- `surya_config.py`: Surya配置优化

### 管理脚本 (scripts/)
- `remote_dev.sh`: 远程服务管理（启动/停止/重启/状态）
- `local_tunnel.sh`: 本地端口转发管理
- `sync_to_remote.sh`: 代码同步到远程服务器
- `test_remote_api.py`: API功能测试

### 测试文件 (tests/)
- `test_single_pdf.py`: 单个PDF测试脚本

### 文档 (docs/)
- 各种项目文档和说明文件

## 使用方法

1. 配置远程环境: `./setup_remote_dev.sh`
2. 启动远程服务: `./scripts/remote_dev.sh start`
3. 建立端口转发: `./scripts/local_tunnel.sh`
4. 访问API: http://localhost:8090
