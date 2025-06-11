# xDAN Smart API - 简化版

基于Surya OCR的PDF转Markdown API服务，支持max_pages功能。

## 主要特性

- ✅ **max_pages支持**: 限制处理页数，从第一页开始
- ✅ **异步处理**: 支持多并发任务
- ✅ **Python兼容**: 修复了Python版本兼容性问题
- ✅ **简单易用**: 保留核心功能，去除复杂配置

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn pypdfium2 pydantic requests aiohttp
```

### 2. 启动服务

```bash
# 使用简单启动脚本
python start_simple.py --port 8080 --host 127.0.0.1 --max-concurrent 3

# 或直接启动
python pdf_to_markdown_api_simple.py --port 8080 --host 127.0.0.1 --max-concurrent 3
```

### 3. 获取API密钥

服务启动时会自动生成默认API密钥，从控制台输出中复制。

### 4. 测试服务

```bash
# 更新test_max_pages.py中的API_KEY
python test_max_pages.py
```

## API端点

### 文件上传转换
```
POST /convert
```

参数：
- `file`: PDF文件
- `max_pages`: 最大处理页数（可选）
- `enable_math`: 是否启用数学公式识别
- `task_name`: OCR任务类型

### URL转换
```
POST /convert-url
```

请求体：
```json
{
    "url": "https://example.com/document.pdf",
    "max_pages": 5,
    "enable_math": true,
    "task_name": "ocr_with_boxes"
}
```

### 批量转换
```
POST /convert-batch
```

请求体：
```json
{
    "urls": ["url1.pdf", "url2.pdf"],
    "max_pages": 3,
    "enable_math": true,
    "task_name": "ocr_with_boxes"
}
```

### 查看任务状态
```
GET /status/{task_id}
```

### 健康检查
```
GET /health
```

## max_pages功能说明

- `max_pages=None`: 处理所有页面（默认）
- `max_pages=1`: 只处理第1页
- `max_pages=5`: 处理前5页
- `max_pages=10`: 处理前10页

## 使用示例

### Python客户端

```python
import requests

# API配置
API_URL = "http://127.0.0.1:8080"
API_KEY = "your_api_key_here"

# 转换PDF（只处理前3页）
response = requests.post(
    f"{API_URL}/convert-url",
    json={
        "url": "https://arxiv.org/pdf/2301.13688.pdf",
        "max_pages": 3,
        "enable_math": True
    },
    headers={"X-API-Key": API_KEY}
)

task_id = response.json()["task_id"]

# 检查状态
status_response = requests.get(
    f"{API_URL}/status/{task_id}",
    headers={"X-API-Key": API_KEY}
)

result = status_response.json()
if result["status"] == "completed":
    markdown = result["markdown"]
    print(f"处理了 {result['processed_pages']} 页")
```

### curl示例

```bash
# 提交转换任务
curl -X POST "http://127.0.0.1:8080/convert-url" \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://arxiv.org/pdf/2301.13688.pdf",
    "max_pages": 3,
    "enable_math": true
  }'

# 检查任务状态
curl -X GET "http://127.0.0.1:8080/status/task_id_here" \
  -H "X-API-Key: your_api_key_here"
```

## 性能优化

- 自动检测GPU/CPU配置
- 智能批处理大小调整
- 异步并发处理
- 线程池优化

## 故障排除

### Python版本兼容性错误
```
device: torch.device | str | None = settings.TORCH_DEVICE_MODEL,
```

**解决方案**: 使用简化版API，已修复此问题。

### 依赖缺失
运行 `python start_simple.py` 会自动检查并提示安装缺失的依赖。

### 内存不足
降低 `--max-concurrent` 参数值。

## 文件说明

- `pdf_to_markdown_api_simple.py`: 简化版API主文件
- `start_simple.py`: 简单启动脚本
- `test_max_pages.py`: max_pages功能测试脚本
- `surya_config.py`: 性能优化配置（可选）

## 与原版差异

| 功能 | 原版 | 简化版 |
|------|------|--------|
| page_range | ✅ 支持复杂范围 | ❌ 移除 |
| max_pages | ❌ 无 | ✅ 简单易用 |
| Python兼容性 | ❌ 需要3.10+ | ✅ 支持3.8+ |
| 配置复杂度 | 🔴 复杂 | 🟢 简单 |
| 核心功能 | ✅ 完整 | ✅ 保留 |

## 总结

简化版API专注于核心功能，提供了：
1. **max_pages功能**: 简单直观的页数限制
2. **Python兼容性**: 修复了版本兼容问题
3. **易于使用**: 减少了配置复杂度
4. **性能优化**: 保留了异步处理能力

适合需要简单、稳定的PDF转Markdown服务的场景。 