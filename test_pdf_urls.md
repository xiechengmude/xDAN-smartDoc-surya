# 测试PDF文件列表

以下是用于测试PDF转Markdown API的PDF文件URL列表：

## 1. 中国科协文件
- **URL**: https://www.cast.org.cn/cms_files/filemanager/583933374/attach/20235/c8003514d41a4625a0d36b3c9dbd7ae3.pdf
- **描述**: 中国科协相关文档
- **预期**: 中文文档，可能包含表格和图表

## 2. 浙江大学实验室简介
- **URL**: http://www.itpe.zju.edu.cn/itpeceu/webshare/2009%C4%EA%CA%B5%D1%E9%CA%D2%BC%F2%BD%E9.pdf
- **描述**: 2009年实验室简介
- **预期**: 中文文档，可能包含实验室介绍和设备信息

## 3. 中国科协附件文档
- **URL**: https://sj.cast.org.cn/cms_files/filemanager/583933374/attach/20235/3c808c4c65be4cf9b4100782e4e33046.pdf
- **描述**: 科协数据相关文档
- **预期**: 中文技术文档

## 4. 澳门科技大学年度学术报告
- **URL**: https://www.must.edu.mo/images/RATO/publication/2008-annual-academic-report.pdf
- **描述**: 2008年度学术报告
- **预期**: 英文学术报告，可能包含图表和数据

## 5. 生物多样性公约文档
- **URL**: https://www.cbd.int/doc/c/d851/4e37/449bb1fdb754412f1ab5d9c5/cop-14-l-06-zh.pdf
- **描述**: COP-14会议文档（中文）
- **预期**: 正式会议文档，结构化内容

## 6. IFC环境社会标准指导说明
- **URL**: https://www.ifc.org/content/dam/ifc/doc/2010/20190627-ifc-ps-guidance-note-6-cn.pdf
- **描述**: IFC环境和社会可持续性标准指导说明6（中文版）
- **预期**: 技术指导文档，可能包含表格和列表

## 7. 生态环境部标准文件
- **URL**: https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/stzl/202011/W020201127553309828533.pdf
- **描述**: 生态环境部发布的标准文件
- **预期**: 官方标准文档，格式规范

## 8. 生态环境部公告
- **URL**: https://www.mee.gov.cn/gkml/hbb/bgt/201707/W020170728397753220005.pdf
- **描述**: 生态环境部公告文件
- **预期**: 政府公告，正式文档格式

## 9. 生物多样性公约决定
- **URL**: https://www.cbd.int/doc/decisions/cop-14/cop-14-dec-08-zh.pdf
- **描述**: COP-14决定文档（中文）
- **预期**: 国际条约决定文档

## 10. IUCN保护区指南
- **URL**: https://portals.iucn.org/library/sites/library/files/documents/PAG-008-Zh.pdf
- **描述**: IUCN保护区管理指南（中文版）
- **预期**: 技术指南文档，可能包含图表和案例研究

## 测试说明

这些PDF文件涵盖了不同类型的文档：
- 中文和英文文档
- 学术报告和技术文档
- 政府公告和国际组织文件
- 不同的文档结构和格式

## 测试命令

### 使用curl测试单个PDF：

```bash
# 1. 下载PDF
curl -o test.pdf "https://www.ifc.org/content/dam/ifc/doc/2010/20190627-ifc-ps-guidance-note-6-cn.pdf"

# 2. 转换PDF
curl -X POST http://localhost:8090/convert \
  -F "file=@test.pdf" \
  -F "max_pages=3" \
  -F "task_type=ocr_without_boxes" \
  -o result.json

# 3. 查看结果
cat result.json | jq '.markdown' > result.md
```

### 使用Python测试：

```python
import requests

# 下载PDF
url = "https://www.ifc.org/content/dam/ifc/doc/2010/20190627-ifc-ps-guidance-note-6-cn.pdf"
response = requests.get(url)
with open("test.pdf", "wb") as f:
    f.write(response.content)

# 转换PDF
with open("test.pdf", "rb") as f:
    files = {"file": ("test.pdf", f, "application/pdf")}
    data = {"max_pages": 3, "task_type": "ocr_without_boxes"}
    response = requests.post("http://localhost:8090/convert", files=files, data=data)
    
if response.status_code == 200:
    result = response.json()
    with open("result.md", "w", encoding="utf-8") as f:
        f.write(result["markdown"])
    print(f"转换成功，页面数：{result['page_count']}")
```

## 远程服务管理

```bash
# 查看服务状态
./scripts/remote_dev.sh pdf_parser status

# 查看服务日志
ssh pdf_parser 'tmux attach-session -t surya-api'

# 重启服务
./scripts/remote_dev.sh pdf_parser restart

# 停止服务
./scripts/remote_dev.sh pdf_parser stop
```