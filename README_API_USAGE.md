# xDAN Smart API 使用总结

## 🎯 快速开始

用户现在可以通过以下几种方式调用高性能的PDF转Markdown API：

### 🚀 最简单的方式 - 运行快速开始脚本

```bash
python quick_start.py
```

这个脚本会自动转换一个示例PDF并保存为 `output.md`。

### 📋 API 基本信息

- **服务地址**: `http://159.54.182.15:8000`
- **API密钥**: `QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM`
- **支持格式**: PDF → Markdown
- **处理性能**: 约1页/秒

## 🛠️ 使用方式

### 1. Python 客户端类（推荐）

```python
from client_example import XDANSmartClient

# 创建客户端
client = XDANSmartClient()

# 转换PDF
markdown = client.convert_from_url("https://example.com/document.pdf", "output.md")
```

### 2. 简单函数调用

```python
from quick_start import convert_pdf

# 一键转换
markdown = convert_pdf("https://example.com/document.pdf")
```

### 3. 原始API调用

```python
import requests

# 提交任务
response = requests.post("http://159.54.182.15:8000/convert-url", 
    headers={"X-API-Key": "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"},
    json={"url": "https://example.com/document.pdf"})

task_id = response.json()["task_id"]

# 查询状态
status_response = requests.get(f"http://159.54.182.15:8000/status/{task_id}",
    headers={"X-API-Key": "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"})
```

### 4. cURL 命令行

```bash
# 提交转换任务
curl -X POST "http://159.54.182.15:8000/convert-url" \
  -H "X-API-Key: QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/document.pdf"}'

# 查询状态
curl -X GET "http://159.54.182.15:8000/status/task_1" \
  -H "X-API-Key: QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"
```

## 📚 可用的脚本和工具

### 客户端脚本
- `quick_start.py` - 最简单的使用方式
- `client_example.py` - 完整的客户端类示例
- `simple_test.py` - 基本连接测试

### 性能测试脚本
- `concurrent_test.py` - 并发性能测试（推荐）
- `test_remote_performance.py` - 完整性能测试套件
- `quick_performance_test.py` - 快速性能测试

### 文档
- `USER_GUIDE.md` - 详细使用指南
- `PERFORMANCE_TEST_REPORT.md` - 性能测试报告
- `REMOTE_SERVER_STARTUP.md` - 服务器启动指南

## 🔧 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/convert-url` | POST | 通过URL转换PDF |
| `/convert` | POST | 上传文件转换 |
| `/status/{task_id}` | GET | 查询转换状态 |

## 📊 性能特点

根据实际测试结果：

- ✅ **成功率**: 100%
- ⚡ **处理速度**: 0.99-1.03秒/页
- 🚀 **并发支持**: 1.07x加速比
- 🔧 **稳定性**: 优秀，生产环境就绪

## 🎯 使用建议

### 新手用户
1. 直接运行 `python quick_start.py`
2. 查看生成的 `output.md` 文件
3. 修改脚本中的PDF URL进行测试

### 开发者
1. 使用 `client_example.py` 中的 `XDANSmartClient` 类
2. 集成到自己的项目中
3. 参考 `USER_GUIDE.md` 了解详细用法

### 系统管理员
1. 运行 `concurrent_test.py` 进行性能测试
2. 查看 `PERFORMANCE_TEST_REPORT.md` 了解性能指标
3. 使用 `REMOTE_SERVER_STARTUP.md` 管理服务器

## 🚨 注意事项

1. **API密钥**: 请妥善保管API密钥，不要泄露
2. **网络连接**: 确保能访问远程服务器
3. **文件大小**: 大文件处理时间较长，请耐心等待
4. **并发限制**: 建议控制并发请求数量

## 🔍 故障排查

### 常见问题

1. **502 Bad Gateway**: 服务器暂时不可用，稍后重试
2. **403 Forbidden**: API密钥错误
3. **404 Not Found**: 任务ID不存在或已过期
4. **超时**: 网络连接问题或文件过大

### 解决方案

1. 检查网络连接
2. 验证API密钥
3. 确认PDF文件可访问
4. 适当增加超时时间

## 🎉 开始使用

选择适合您的方式开始使用：

```bash
# 最简单的方式
python quick_start.py

# 完整示例
python client_example.py

# 性能测试
python concurrent_test.py
```

**祝您使用愉快！** 🚀 