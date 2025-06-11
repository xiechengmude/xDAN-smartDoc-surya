import argparse
import asyncio
import io
import os
import re
import secrets
from typing import List, Optional, Dict, Union
import requests
from concurrent.futures import ThreadPoolExecutor
import time

import pypdfium2
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Depends, Header, Security, Query
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
import uvicorn

from surya.models import load_predictors
from surya.common.surya.schema import TaskNames
from surya.settings import settings
from surya.input.load import load_pdf
from surya.scripts.config import CLILoader

# 导入性能优化配置
try:
    from surya_config import setup_environment_variables
    # 应用性能优化设置
    recommended_settings = setup_environment_variables()
except ImportError:
    print("⚠️ 未找到surya_config.py，使用默认配置")
    recommended_settings = {
        "max_concurrent_tasks": 10,
        "default_batch_size": 32,
        "thread_pool_workers": 16
    }

# 设置环境变量以避免MPS问题
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

app = FastAPI(
    title="xDAN Smart API",
    description="高性能异步的 PDF 到 Markdown 转换服务，基于 xDAN Smart OCR",
    version="2.0.0",
)

# 全局变量存储预加载的模型
predictors = None

# 全局变量存储任务状态
tasks = {}

# 最大并发数（从性能优化配置获取，可通过命令行参数修改）
MAX_CONCURRENT_TASKS = recommended_settings.get("max_concurrent_tasks", 20)

# 信号量用于限制并发任务数
task_semaphore = None

# 线程池用于CPU密集型任务
thread_pool = None

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
    if not api_key_header:
        print(f"API请求缺少密钥 - 来源IP可能需要提供X-API-Key头部")
        raise HTTPException(
            status_code=403, 
            detail="缺少 API 密钥。请在请求头中提供 X-API-Key。"
        )
    
    if api_key_header in API_KEYS:
        return api_key_header
    
    print(f"无效的API密钥尝试: {api_key_header[:8]}... - 请检查密钥是否正确")
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
    total_pages: Optional[int] = None
    processed_pages: Optional[List[int]] = None
    processing_time: Optional[float] = None


class ConversionRequest(BaseModel):
    """转换请求模型"""
    page_range: Optional[str] = Field(None, description="页面范围，例如: '0,5-10,20' 或 '1-5'")
    enable_math: bool = Field(True, description="是否启用数学公式识别")
    task_name: str = Field("ocr_with_boxes", description="OCR任务类型: ocr_with_boxes, ocr_without_boxes, block_without_boxes")
    batch_size: Optional[int] = Field(None, description="批处理大小，用于性能优化")


class UrlConvertRequest(BaseModel):
    url: str
    page_range: Optional[str] = Field(None, description="页面范围，例如: '0,5-10,20' 或 '1-5'")
    enable_math: bool = Field(True, description="是否启用数学公式识别")
    task_name: str = Field("ocr_with_boxes", description="OCR任务类型")
    batch_size: Optional[int] = Field(None, description="批处理大小")


class BatchConversionRequest(BaseModel):
    """批量转换请求模型"""
    urls: List[str] = Field(..., description="PDF文件URL列表")
    page_range: Optional[str] = Field(None, description="应用于所有PDF的页面范围")
    enable_math: bool = Field(True, description="是否启用数学公式识别")
    task_name: str = Field("ocr_with_boxes", description="OCR任务类型")


def parse_page_range(page_range_str: str) -> List[int]:
    """解析页面范围字符串"""
    if not page_range_str:
        return None
    
    range_lst = page_range_str.split(",")
    page_lst = []
    for i in range_lst:
        if "-" in i:
            start, end = i.split("-")
            page_lst += list(range(int(start), int(end) + 1))
        else:
            page_lst.append(int(i))
    page_lst = sorted(list(set(page_lst)))  # 去重并排序
    return page_lst


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


async def process_pdf_optimized(
    task_id: str, 
    pdf_bytes: bytes, 
    page_range: Optional[List[int]] = None,
    enable_math: bool = True,
    task_name: str = "ocr_with_boxes",
    batch_size: Optional[int] = None
):
    """优化的异步PDF处理函数，支持页面范围和批处理"""
    # 使用信号量限制并发任务数
    async with task_semaphore:
        start_time = time.time()
        try:
            # 更新任务状态为处理中
            tasks[task_id] = {
                "status": "processing", 
                "markdown": None, 
                "error": None,
                "total_pages": None,
                "processed_pages": None,
                "processing_time": None
            }
            
            # 使用pypdfium2加载PDF文件
            pdf = pypdfium2.PdfDocument(pdf_bytes)
            total_pages = len(pdf)
            
            # 确定要处理的页面
            if page_range is None:
                pages_to_process = list(range(total_pages))
            else:
                # 验证页面范围
                invalid_pages = [p for p in page_range if p < 0 or p >= total_pages]
                if invalid_pages:
                    raise ValueError(f"无效的页面范围: {invalid_pages}，PDF总共有 {total_pages} 页")
                pages_to_process = page_range
            
            # 存储所有页面的Markdown内容
            all_markdown = []
            
            # 根据任务名称选择处理方式
            task_names = [getattr(TaskNames, task_name)]
            
            # 批处理页面以提高性能
            default_batch_size = recommended_settings.get("default_batch_size", 32 if settings.TORCH_DEVICE_MODEL != "cpu" else 8)
            effective_batch_size = batch_size or default_batch_size
            
            for i in range(0, len(pages_to_process), effective_batch_size):
                batch_pages = pages_to_process[i:i + effective_batch_size]
                batch_images = []
                batch_highres_images = []
                
                # 并行渲染页面图像
                def render_page(page_idx):
                    page = pdf[page_idx]
                    # 标准分辨率图像用于检测
                    img = page.render(scale=settings.IMAGE_DPI / 72).to_pil().convert("RGB")
                    # 高分辨率图像用于OCR
                    highres_img = page.render(scale=settings.IMAGE_DPI_HIGHRES / 72).to_pil().convert("RGB")
                    return img, highres_img
                
                # 使用线程池并行处理图像渲染
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=min(len(batch_pages), 4)) as executor:
                    render_tasks = [
                        loop.run_in_executor(executor, render_page, page_idx)
                        for page_idx in batch_pages
                    ]
                    rendered_results = await asyncio.gather(*render_tasks)
                
                for img, highres_img in rendered_results:
                    batch_images.append(img)
                    batch_highres_images.append(highres_img)
                
                # 批量OCR处理
                batch_predictions = predictors["recognition"](
                    batch_images,
                    task_names=task_names,
                    det_predictor=predictors["detection"],
                    highres_images=batch_highres_images,
                    math_mode=enable_math,
                    return_words=True,
                )
                
                # 处理批次结果
                for j, (page_idx, img_pred) in enumerate(zip(batch_pages, batch_predictions)):
                    # 提取文本行
                    page_text = "\n\n".join([replace_fences(line.text) for line in img_pred.text_lines])
                    
                    # 添加页码标记
                    page_header = f"\n\n## 第 {page_idx + 1} 页\n\n"
                    all_markdown.append(page_header + page_text)
                
                # 更新处理进度
                processed_count = min(i + effective_batch_size, len(pages_to_process))
                tasks[task_id]["processed_pages"] = pages_to_process[:processed_count]
            
            # 合并所有页面的Markdown内容
            final_markdown = "\n".join(all_markdown)
            processing_time = time.time() - start_time
            
            # 更新任务状态为完成
            tasks[task_id] = {
                "status": "completed", 
                "markdown": final_markdown, 
                "error": None,
                "total_pages": total_pages,
                "processed_pages": pages_to_process,
                "processing_time": processing_time
            }
            
        except Exception as e:
            # 如果处理过程中出现错误，更新任务状态为失败
            processing_time = time.time() - start_time
            tasks[task_id] = {
                "status": "failed", 
                "markdown": None, 
                "error": str(e),
                "total_pages": None,
                "processed_pages": None,
                "processing_time": processing_time
            }
            print(f"处理PDF时出错: {e}")


async def process_pdf_batch(task_id: str, pdf_urls: List[str], **kwargs):
    """批量处理多个PDF文件"""
    async with task_semaphore:
        start_time = time.time()
        try:
            tasks[task_id] = {
                "status": "processing", 
                "markdown": None, 
                "error": None,
                "total_files": len(pdf_urls),
                "processed_files": 0,
                "processing_time": None
            }
            
            all_results = []
            
            for i, url in enumerate(pdf_urls):
                try:
                    # 下载PDF
                    response = requests.get(url, stream=True, timeout=30)
                    response.raise_for_status()
                    pdf_bytes = response.content
                    
                    # 创建子任务ID
                    sub_task_id = f"{task_id}_file_{i}"
                    
                    # 处理单个PDF
                    await process_pdf_optimized(sub_task_id, pdf_bytes, **kwargs)
                    
                    # 获取结果
                    if sub_task_id in tasks and tasks[sub_task_id]["status"] == "completed":
                        all_results.append({
                            "url": url,
                            "markdown": tasks[sub_task_id]["markdown"],
                            "total_pages": tasks[sub_task_id]["total_pages"],
                            "processed_pages": tasks[sub_task_id]["processed_pages"]
                        })
                        # 清理子任务
                        del tasks[sub_task_id]
                    else:
                        all_results.append({
                            "url": url,
                            "error": tasks.get(sub_task_id, {}).get("error", "未知错误")
                        })
                    
                    # 更新进度
                    tasks[task_id]["processed_files"] = i + 1
                    
                except Exception as e:
                    all_results.append({
                        "url": url,
                        "error": str(e)
                    })
            
            processing_time = time.time() - start_time
            
            # 合并所有结果
            combined_markdown = "\n\n---\n\n".join([
                result["markdown"] for result in all_results 
                if "markdown" in result and result["markdown"]
            ])
            
            tasks[task_id] = {
                "status": "completed",
                "markdown": combined_markdown,
                "error": None,
                "results": all_results,
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            tasks[task_id] = {
                "status": "failed",
                "markdown": None,
                "error": str(e),
                "processing_time": processing_time
            }


@app.on_event("startup")
async def startup_event():
    """启动时加载模型和初始化资源"""
    global predictors, task_semaphore, thread_pool
    
    # 加载模型
    predictors = load_predictors()
    
    # 创建默认 API 密钥
    default_key = generate_api_key("default")
    print(f"\n默认 API 密钥已生成: {default_key}\n")
    
    # 初始化信号量用于限制并发任务数
    task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    print(f"最大并发任务数设置为: {MAX_CONCURRENT_TASKS}")
    
    # 初始化线程池
    thread_pool_workers = recommended_settings.get("thread_pool_workers", min(32, os.cpu_count() + 4))
    thread_pool = ThreadPoolExecutor(max_workers=thread_pool_workers)
    
    # 打印性能优化信息
    print(f"设备: {settings.TORCH_DEVICE_MODEL}")
    print(f"检测批处理大小: {settings.DETECTOR_BATCH_SIZE}")
    print(f"识别批处理大小: {settings.RECOGNITION_BATCH_SIZE}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    global thread_pool
    if thread_pool:
        thread_pool.shutdown(wait=True)


@app.post("/convert", response_model=ConversionResult)
async def convert_pdf_to_markdown(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    page_range: Optional[str] = Query(None, description="页面范围，例如: '0,5-10,20'"),
    enable_math: bool = Query(True, description="是否启用数学公式识别"),
    task_name: str = Query("ocr_with_boxes", description="OCR任务类型"),
    batch_size: Optional[int] = Query(None, description="批处理大小"),
    api_key: str = Depends(get_api_key),
):
    """
    将PDF文件转换为Markdown格式（支持页面范围）
    
    - **file**: PDF文件
    - **page_range**: 页面范围，例如 "0,5-10,20" 表示处理第0页、第5-10页和第20页
    - **enable_math**: 是否启用数学公式识别
    - **task_name**: OCR任务类型 (ocr_with_boxes, ocr_without_boxes, block_without_boxes)
    - **batch_size**: 批处理大小，用于性能优化
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    # 检查文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 读取文件内容
    pdf_bytes = await file.read()
    
    # 解析页面范围
    parsed_page_range = None
    if page_range:
        try:
            parsed_page_range = parse_page_range(page_range)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的页面范围格式: {str(e)}")
    
    # 生成任务ID
    task_id = f"task_{int(time.time() * 1000)}_{len(tasks)}"
    
    # 在后台异步处理PDF
    background_tasks.add_task(
        process_pdf_optimized, 
        task_id, 
        pdf_bytes, 
        parsed_page_range,
        enable_math,
        task_name,
        batch_size
    )
    
    return ConversionResult(task_id=task_id, status="processing")


@app.post("/convert-url", response_model=ConversionResult)
async def convert_pdf_from_url(
    request: UrlConvertRequest,
    api_key: str = Depends(get_api_key),
):
    """
    通过URL下载PDF文件并转换为Markdown格式（支持页面范围）
    
    - **url**: PDF文件的URL
    - **page_range**: 页面范围，例如 "0,5-10,20"
    - **enable_math**: 是否启用数学公式识别
    - **task_name**: OCR任务类型
    - **batch_size**: 批处理大小
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    try:
        # 下载PDF文件
        response = requests.get(request.url, stream=True, timeout=30)
        response.raise_for_status()
        
        # 检查内容类型
        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type.lower() and not request.url.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="URL不指向PDF文件")
        
        # 读取文件内容
        pdf_bytes = response.content
        
        # 解析页面范围
        parsed_page_range = None
        if request.page_range:
            try:
                parsed_page_range = parse_page_range(request.page_range)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"无效的页面范围格式: {str(e)}")
        
        # 生成任务ID
        task_id = f"task_{int(time.time() * 1000)}_{len(tasks)}"
        
        # 在后台异步处理PDF
        asyncio.create_task(process_pdf_optimized(
            task_id, 
            pdf_bytes, 
            parsed_page_range,
            request.enable_math,
            request.task_name,
            request.batch_size
        ))
        
        return ConversionResult(task_id=task_id, status="processing")
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"下载PDF文件失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理PDF文件时出错: {str(e)}")


@app.post("/convert-batch", response_model=ConversionResult)
async def convert_pdf_batch(
    request: BatchConversionRequest,
    api_key: str = Depends(get_api_key),
):
    """
    批量转换多个PDF文件
    
    - **urls**: PDF文件URL列表
    - **page_range**: 应用于所有PDF的页面范围
    - **enable_math**: 是否启用数学公式识别
    - **task_name**: OCR任务类型
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    if len(request.urls) > 10:  # 限制批量处理的文件数量
        raise HTTPException(status_code=400, detail="批量处理最多支持10个文件")
    
    # 解析页面范围
    parsed_page_range = None
    if request.page_range:
        try:
            parsed_page_range = parse_page_range(request.page_range)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的页面范围格式: {str(e)}")
    
    # 生成任务ID
    task_id = f"batch_{int(time.time() * 1000)}_{len(tasks)}"
    
    # 在后台异步处理批量PDF
    asyncio.create_task(process_pdf_batch(
        task_id,
        request.urls,
        page_range=parsed_page_range,
        enable_math=request.enable_math,
        task_name=request.task_name
    ))
    
    return ConversionResult(task_id=task_id, status="processing")


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
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"找不到任务ID: {task_id}")
    
    result = tasks[task_id]
    
    response = ConversionResult(
        task_id=task_id,
        status=result.get("status", "unknown"),
        total_pages=result.get("total_pages"),
        processed_pages=result.get("processed_pages"),
        processing_time=result.get("processing_time")
    )
    
    if result.get("status") == "completed":
        response.markdown = result.get("markdown")
    elif result.get("status") == "failed":
        response.error = result.get("error")
    
    return response


@app.get("/tasks")
async def list_tasks(
    api_key: str = Depends(get_api_key),
    status: Optional[str] = Query(None, description="按状态过滤任务")
):
    """列出所有任务"""
    filtered_tasks = {}
    for task_id, task_info in tasks.items():
        if status is None or task_info.get("status") == status:
            # 不返回markdown内容以减少响应大小
            filtered_tasks[task_id] = {
                k: v for k, v in task_info.items() 
                if k != "markdown"
            }
    return filtered_tasks


@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    api_key: str = Depends(get_api_key),
):
    """删除指定任务"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"找不到任务ID: {task_id}")
    
    del tasks[task_id]
    return {"message": f"任务 {task_id} 已删除"}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "device": settings.TORCH_DEVICE_MODEL,
        "active_tasks": len([t for t in tasks.values() if t.get("status") == "processing"]),
        "total_tasks": len(tasks)
    }


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

@app.get("/validate-key")
async def validate_api_key(api_key: str = Depends(get_api_key)):
    """验证API密钥是否有效"""
    key_name = API_KEYS.get(api_key, "unknown")
    return {
        "valid": True,
        "key_name": key_name,
        "message": "API密钥有效"
    }

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="xDAN Smart API - PDF 到 Markdown 转换服务")
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="API 服务端口号（默认：8000）"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0", 
        help="API 服务主机地址（默认：0.0.0.0）"
    )
    parser.add_argument(
        "--max-concurrent", 
        type=int, 
        default=5, 
        help="最大并发任务数（默认：5）"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="启用代码热重载（开发模式）"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置全局最大并发数
    MAX_CONCURRENT_TASKS = args.max_concurrent
    
    # 启动服务
    uvicorn.run(
        "pdf_to_markdown_api:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload
    )
