# xDAN Smart API 文档

## 简介

这是一个基于 xDAN Smart OCR 工具包开发的高性能异步 PDF 到 Markdown 转换 API 服务。该服务可以将 PDF 文件转换为 Markdown 格式，支持多语言文本识别和数学公式转换。

## API 基本信息

- **基础 URL**: `http://159.54.182.15:8000`
- **API 版本**: v1.0.0
- **内容类型**: `multipart/form-data` (上传文件), `application/json` (其他请求)

## 认证

所有 API 请求都需要使用 API 密钥进行认证。API 密钥应通过 HTTP 头部 `X-API-Key` 提供。

```
X-API-Key: your_api_key_here
```

### 获取 API 密钥

系统启动时会自动生成一个默认 API 密钥，并在控制台输出。管理员也可以通过管理端点生成新的 API 密钥。

### API 密钥管理

管理员可以通过以下端点管理 API 密钥：

1. **生成新密钥**：
   - URL: `/admin/generate-key`
   - 方法: `POST`
   - 头部: `admin_key: xdan-admin-secret`
   - 请求体: `{"key_name": "客户名称"}`

2. **列出所有密钥**：
   - URL: `/admin/list-keys`
   - 方法: `GET`
   - 头部: `admin_key: xdan-admin-secret`

## API 端点

### 1. 转换 PDF 到 Markdown

将 PDF 文件上传并开始异步转换为 Markdown。

- **URL**: `/convert`
- **方法**: `POST`
- **内容类型**: `multipart/form-data`

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| file  | File | 是   | 要转换的 PDF 文件 |

#### 响应

```json
{
  "task_id": "task_1",
  "status": "processing"
}
```

| 字段名   | 类型   | 描述 |
|---------|-------|------|
| task_id | 字符串 | 任务 ID，用于后续查询转换状态 |
| status  | 字符串 | 任务状态，初始为 "processing" |

#### 示例

**cURL**:
```bash
curl -X POST -F "file=@文件路径.pdf" -H "X-API-Key: your_api_key_here" http://159.54.182.15:8000/convert
```

**Python**:
```python
import requests

url = "http://159.54.182.15:8000/convert"
headers = {"X-API-Key": "your_api_key_here"}
files = {"file": open("文件路径.pdf", "rb")}
response = requests.post(url, files=files, headers=headers)
print(response.json())
```

### 2. 查询转换状态

查询 PDF 到 Markdown 转换任务的状态和结果。

- **URL**: `/status/{task_id}`
- **方法**: `GET`
- **内容类型**: `application/json`

#### 路径参数

| 参数名   | 类型   | 描述 |
|---------|-------|------|
| task_id | 字符串 | 任务 ID |

#### 响应

**处理中**:
```json
{
  "task_id": "task_1",
  "status": "processing",
  "markdown": null,
  "error": null
}
```

**完成**:
```json
{
  "task_id": "task_1",
  "status": "completed",
  "markdown": "# 转换后的 Markdown 内容...",
  "error": null
}
```

**失败**:
```json
{
  "task_id": "task_1",
  "status": "failed",
  "markdown": null,
  "error": "转换过程中出现错误: ..."
}
```

| 字段名    | 类型   | 描述 |
|----------|-------|------|
| task_id  | 字符串 | 任务 ID |
| status   | 字符串 | 任务状态: "processing", "completed", "failed" |
| markdown | 字符串 | 转换后的 Markdown 内容，仅在状态为 "completed" 时有值 |
| error    | 字符串 | 错误信息，仅在状态为 "failed" 时有值 |

#### 示例

**cURL**:
```bash
curl -H "X-API-Key: your_api_key_here" http://159.54.182.15:8000/status/task_1
```

**Python**:
```python
import requests

url = "http://159.54.182.15:8000/status/task_1"
headers = {"X-API-Key": "your_api_key_here"}
response = requests.get(url, headers=headers)
print(response.json())
```

## 完整使用流程

1. 上传 PDF 文件并获取任务 ID
2. 定期查询任务状态，直到状态变为 "completed" 或 "failed"
3. 如果状态为 "completed"，从响应中获取 Markdown 内容
4. 如果状态为 "failed"，从响应中获取错误信息

### Python 示例代码

```python
import requests
import time

# API 密钥
api_key = "your_api_key_here"
headers = {"X-API-Key": api_key}

# 1. 上传 PDF 文件
upload_url = "http://159.54.182.15:8000/convert"
files = {"file": open("example.pdf", "rb")}
response = requests.post(upload_url, files=files, headers=headers)
task_data = response.json()
task_id = task_data["task_id"]

# 2. 查询任务状态
status_url = f"http://159.54.182.15:8000/status/{task_id}"
while True:
    response = requests.get(status_url, headers=headers)
    status_data = response.json()
    
    if status_data["status"] == "completed":
        # 3. 获取 Markdown 内容
        markdown_content = status_data["markdown"]
        with open("output.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print("转换完成，已保存到 output.md")
        break
    elif status_data["status"] == "failed":
        # 4. 获取错误信息
        error_message = status_data["error"]
        print(f"转换失败: {error_message}")
        break
    else:
        print("正在处理中...")
        time.sleep(5)  # 等待 5 秒后再次查询
```

## 错误代码

| 状态码 | 错误类型 | 描述 |
|-------|---------|------|
| 400   | Bad Request | 请求格式错误，例如上传的不是 PDF 文件 |
| 403   | Forbidden | 无效的 API 密钥或权限不足 |
| 404   | Not Found | 任务 ID 不存在 |
| 500   | Internal Server Error | 服务器内部错误 |

## 服务器配置与启动

### 命令行参数

API 服务支持通过命令行参数进行配置，包括指定端口、主机地址和最大并发任务数等。

```bash
python pdf_to_markdown_api.py --port 8080 --host 0.0.0.0 --max-concurrent 10 --reload
```

| 参数 | 类型 | 默认值 | 描述 |
|--------|------|---------|------|
| `--port` | 整数 | 8000 | API 服务端口号 |
| `--host` | 字符串 | "0.0.0.0" | API 服务主机地址 |
| `--max-concurrent` | 整数 | 5 | 最大并发任务数 |
| `--reload` | 布尔标志 | 否 | 启用代码热重载（开发模式） |

### 并发控制

API 服务使用信号量机制限制并发处理的 PDF 文件数量，默认为 5 个。这意味着服务器同时最多只会处理 5 个 PDF 文件，其余的请求将被排队等待。这有助于防止服务器资源过载。

如果您的服务器有更强的处理能力，可以通过 `--max-concurrent` 参数增加并发数。

## 注意事项

1. **文件大小限制**: 默认最大支持 100MB 的 PDF 文件
2. **处理时间**: 处理时间取决于 PDF 文件的大小、复杂度和服务器负载
3. **并发限制**: 服务器默认并发限制为 5 个任务，可通过命令行参数调整
4. **数学公式**: 支持识别和转换数学公式，转换后的格式为 LaTeX 格式
5. **多语言支持**: 支持 90+ 种语言的文本识别

## 测试脚本使用

项目包含一个测试脚本 `test_pdf_api.py`，可用于快速测试 API 功能。使用方法如下：

```bash
python test_pdf_api.py --pdf /path/to/your/document.pdf --url http://server-address:port --api-key your_api_key_here --output output.md
```

参数说明：

| 参数 | 描述 | 是否必需 |
|--------|------|--------|
| `--pdf` | PDF 文件路径 | 是 |
| `--url` | API 服务地址，默认为 http://localhost:8000 | 否 |
| `--api-key` | API 密钥 | 是 |
| `--output` | 输出 Markdown 文件路径，如不指定则直接打印到控制台 | 否 |
| `--timeout` | 等待转换完成的超时时间（秒），默认 300 秒 | 否 |
| `--interval` | 检查转换状态的间隔时间（秒），默认 5 秒 | 否 |

### 示例

```bash
# 远程服务器测试
python test_pdf_api.py --pdf tests/法律Agent测试用例.pdf --url http://159.54.182.15:8080 --api-key pgMePwetA3zidEixgzieOCrKHwGRps61cqufII_VJmY --output 法律Agent测试结果.md

# 本地测试
python test_pdf_api.py --pdf tests/法律Agent测试用例.pdf --url http://localhost:8000 --api-key your_local_api_key --output 法律Agent测试结果.md
```

## 服务器状态

如果您需要检查 API 服务器的状态，可以访问 API 文档页面：

```
http://159.54.182.15:8080/docs
```

此页面提供了 API 的交互式文档，您可以直接在浏览器中测试 API 功能。

## 联系与支持

如有任何问题或需要支持，请联系系统管理员。
