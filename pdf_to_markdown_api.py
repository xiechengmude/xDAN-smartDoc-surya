import asyncio
import io
import os
import re
from typing import List, Optional

import pypdfium2
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from surya.models import load_predictors
from surya.common.surya.schema import TaskNames
from surya.settings import settings

# 设置环境变量以避免MPS问题
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

app = FastAPI(
    title="PDF to Markdown API",
    description="高性能异步的 PDF 到 Markdown 转换服务，基于 Surya OCR",
    version="0.1.0",
)

# 全局变量存储预加载的模型
predictors = None


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


@app.post("/convert", response_model=ConversionResult)
async def convert_pdf_to_markdown(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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
async def get_conversion_status(task_id: str):
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


if __name__ == "__main__":
    uvicorn.run("pdf_to_markdown_api:app", host="0.0.0.0", port=8000, reload=True)
