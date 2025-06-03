import asyncio
import io
import os
import re
import secrets
from typing import List, Optional, Dict

import pypdfium2
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Depends, Header, Security
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import uvicorn

from surya.models import load_predictors
from surya.common.surya.schema import TaskNames
from surya.settings import settings

# 设置环境变量以避免MPS问题
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

app = FastAPI(
    title="xDAN Smart API",
    description="高性能异步的 PDF 到 Markdown 转换服务，基于 xDAN Smart OCR",
    version="1.0.0",
)

# 全局变量存储预加载的模型
predictors = None

# API 密钥验证
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# 存储有效的 API 密钥
API_KEYS: Dict[str, str] = {}

# 生成新的 API 密钥
def generate_api_key(key_name: str) -> str:
    """生成新的 API 密钥并存储"""
    api_key = secrets.token_urlsafe(32)
    API_KEYS[api_key] = key_name
    return api_key

# 验证 API 密钥
async def get_api_key(api_key_header: str = Security(api_key_header)):
    """验证 API 密钥是否有效"""
    if api_key_header in API_KEYS:
        return api_key_header
    raise HTTPException(
        status_code=403, 
        detail="无效的 API 密钥。请提供有效的 X-API-Key 头部。"
    )


class ConversionResult(BaseModel):
    """转换结果模型"""
    task_id: str
    status: str
    markdown: Optional[str] = None
    error: Optional[str] = None


# 存储后台任务的结果
conversion_results = {}


def replace_fences(text):
    """替换数学公式标记为Markdown格式"""
    text = re.sub(r'<math display="block">(.*?)</math>', r"$$\1$$", text)
    text = re.sub(r"<math>(.*?)</math>", r"$\1$", text)
    text = re.sub(r'<math display="inline">(.*?)</math>', r"$\1$", text)
    return text


def open_pdf(pdf_bytes):
    """打开PDF文件"""
    stream = io.BytesIO(pdf_bytes)
    return pypdfium2.PdfDocument(stream)


def get_page_image(pdf_doc, page_num, dpi=settings.IMAGE_DPI_HIGHRES):
    """获取PDF页面的图像"""
    renderer = pdf_doc.render(
        pypdfium2.PdfBitmap.to_pil,
        page_indices=[page_num],
        scale=dpi / 72,
    )
    png = list(renderer)[0]
    return png.convert("RGB")


async def process_pdf(pdf_bytes: bytes, task_id: str):
    """处理PDF文件并转换为Markdown"""
    try:
        # 打开PDF文件
        doc = open_pdf(pdf_bytes)
        page_count = len(doc)
        
        # 存储所有页面的文本
        all_text = []
        
        # 处理每一页
        for page_num in range(page_count):
            # 获取页面图像
            pil_image = get_page_image(doc, page_num)
            
            # 使用OCR识别文本
            img_pred = predictors["recognition"](
                [pil_image],
                task_names=[TaskNames.ocr_with_boxes],
                det_predictor=predictors["detection"],
                highres_images=[pil_image],
                math_mode=True,
                return_words=True,
            )[0]
            
            # 提取文本行
            page_text = "\n\n".join([replace_fences(line.text) for line in img_pred.text_lines])
            
            # 添加页码标记
            page_header = f"\n\n## 第 {page_num + 1} 页\n\n"
            all_text.append(page_header + page_text)
        
        # 关闭PDF文档
        doc.close()
        
        # 合并所有文本
        markdown_text = "\n".join(all_text)
        
        # 存储结果
        conversion_results[task_id] = {
            "status": "completed",
            "markdown": markdown_text
        }
        
    except Exception as e:
        # 存储错误信息
        conversion_results[task_id] = {
            "status": "failed",
            "error": str(e)
        }


@app.on_event("startup")
async def startup_event():
    """启动时加载模型"""
    global predictors
    predictors = load_predictors()
    
    # 创建默认 API 密钥
    default_key = generate_api_key("default")
    print(f"\n默认 API 密钥已生成: {default_key}\n")


@app.post("/convert", response_model=ConversionResult)
async def convert_pdf_to_markdown(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key),
):
    """
    将PDF文件转换为Markdown格式
    
    - **file**: PDF文件
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只接受PDF文件")
    
    # 读取文件内容
    pdf_bytes = await file.read()
    
    # 生成任务ID
    task_id = f"task_{len(conversion_results) + 1}"
    
    # 初始化任务状态
    conversion_results[task_id] = {"status": "processing"}
    
    # 添加后台任务
    background_tasks.add_task(process_pdf, pdf_bytes, task_id)
    
    return ConversionResult(
        task_id=task_id,
        status="processing"
    )


@app.get("/status/{task_id}", response_model=ConversionResult)
async def get_conversion_status(
    task_id: str,
    api_key: str = Depends(get_api_key),
):
    """
    获取转换任务的状态
    
    - **task_id**: 任务ID
    
    返回任务状态和结果（如果已完成）
    """
    if task_id not in conversion_results:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    result = conversion_results[task_id]
    
    response = ConversionResult(
        task_id=task_id,
        status=result["status"]
    )
    
    if result["status"] == "completed":
        response.markdown = result["markdown"]
    elif result["status"] == "failed":
        response.error = result["error"]
    
    return response


# API 密钥管理端点
class ApiKeyRequest(BaseModel):
    key_name: str

class ApiKeyResponse(BaseModel):
    key_name: str
    api_key: str

@app.post("/admin/generate-key", response_model=ApiKeyResponse)
async def generate_new_api_key(
    request: ApiKeyRequest,
    admin_key: str = Header(..., description="管理员密钥，用于生成新的 API 密钥")
):
    """生成新的 API 密钥（需要管理员密钥）"""
    # 这里使用一个简单的管理员密钥，实际应用中应该使用更安全的认证方式
    if admin_key != "xdan-admin-secret":
        raise HTTPException(status_code=403, detail="无效的管理员密钥")
    
    api_key = generate_api_key(request.key_name)
    return ApiKeyResponse(key_name=request.key_name, api_key=api_key)

@app.get("/admin/list-keys")
async def list_api_keys(
    admin_key: str = Header(..., description="管理员密钥，用于列出所有 API 密钥")
):
    """列出所有 API 密钥（需要管理员密钥）"""
    if admin_key != "xdan-admin-secret":
        raise HTTPException(status_code=403, detail="无效的管理员密钥")
    
    return {key: name for key, name in API_KEYS.items()}

if __name__ == "__main__":
    uvicorn.run("pdf_to_markdown_api:app", host="0.0.0.0", port=8000, reload=True)
