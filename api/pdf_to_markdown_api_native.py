#!/usr/bin/env python3
"""
基于Surya原生功能的PDF转Markdown API
使用Surya真实的page_range参数和max_pages功能
"""

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

# 设置环境变量以避免MPS问题
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# 延迟导入Surya以避免类型注解问题
def load_surya_modules():
    """延迟加载Surya模块"""
    try:
        from surya.models import load_predictors
        from surya.input.load import load_pdf
        from surya.scripts.config import CLILoader
        from surya.settings import settings
        return load_predictors, load_pdf, CLILoader, settings
    except Exception as e:
        print(f"❌ 加载Surya模块失败: {e}")
        print("请检查Python版本和Surya安装")
        raise

app = FastAPI(
    title="xDAN Smart API - Native",
    description="基于Surya原生功能的PDF到Markdown转换服务",
    version="1.0.0",
)

# 全局变量存储预加载的模型
predictors = None
load_pdf = None
CLILoader = None
settings = None

# 全局变量存储任务状态
tasks = {}

# 最大并发数
MAX_CONCURRENT_TASKS = 3

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
        print(f"API请求缺少密钥")
        raise HTTPException(
            status_code=403, 
            detail="缺少 API 密钥。请在请求头中提供 X-API-Key。"
        )
    
    if api_key_header in API_KEYS:
        return api_key_header
    
    print(f"无效的API密钥尝试: {api_key_header[:8]}...")
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
    processed_pages: Optional[int] = None
    processing_time: Optional[float] = None


class ConvertRequest(BaseModel):
    """转换请求模型"""
    url: Optional[str] = Field(None, description="PDF文件URL")
    max_pages: Optional[int] = Field(None, description="最大处理页数，从第一页开始")
    page_range: Optional[str] = Field(None, description="页面范围，如'0,5-10,20'")
    enable_math: bool = Field(True, description="是否启用数学公式识别")


def parse_page_range(page_range_str: str) -> List[int]:
    """解析页面范围字符串 - 使用Surya原生实现"""
    if not page_range_str:
        return None
    
    # 使用Surya的原生解析方法
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


def max_pages_to_page_range(max_pages: int, total_pages: int) -> List[int]:
    """将max_pages转换为page_range"""
    if max_pages is None:
        return None
    return list(range(min(max_pages, total_pages)))


def replace_fences(text):
    """替换数学公式标记为Markdown格式"""
    text = re.sub(r'<math display="block">(.*?)</math>', r"$$\1$$", text)
    text = re.sub(r"<math>(.*?)</math>", r"$\1$", text)
    text = re.sub(r'<math display="inline">(.*?)</math>', r"$\1$", text)
    return text


async def process_pdf_native(
    task_id: str, 
    pdf_bytes: bytes, 
    max_pages: Optional[int] = None,
    page_range: Optional[str] = None,
    enable_math: bool = True
):
    """使用Surya原生功能处理PDF"""
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
            
            # 保存临时PDF文件
            temp_pdf_path = f"/tmp/temp_{task_id}.pdf"
            with open(temp_pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # 使用pypdfium2获取总页数
            doc = pypdfium2.PdfDocument(pdf_bytes)
            total_pages = len(doc)
            doc.close()
            
            # 确定页面范围
            if page_range:
                # 使用指定的页面范围
                page_list = parse_page_range(page_range)
            elif max_pages:
                # 使用max_pages转换为页面范围
                page_list = max_pages_to_page_range(max_pages, total_pages)
            else:
                # 处理所有页面
                page_list = None
            
            # 使用Surya原生的load_pdf函数
            images, names = load_pdf(temp_pdf_path, page_range=page_list, dpi=settings.IMAGE_DPI)
            highres_images, _ = load_pdf(temp_pdf_path, page_range=page_list, dpi=settings.IMAGE_DPI_HIGHRES)
            
            processed_pages = len(images)
            
            # 使用Surya进行OCR识别
            from surya.common.surya.schema import TaskNames
            task_names = [TaskNames.ocr_with_boxes]
            
            # 批量OCR处理
            predictions = predictors["recognition"](
                images,
                task_names=task_names,
                det_predictor=predictors["detection"],
                highres_images=highres_images,
                math_mode=enable_math,
                return_words=True,
            )
            
            # 处理结果
            all_markdown = []
            for i, (img_pred, name) in enumerate(zip(predictions, names)):
                # 提取文本行
                page_text = "\n\n".join([replace_fences(line.text) for line in img_pred.text_lines])
                
                # 添加页码标记
                page_num = page_list[i] + 1 if page_list else i + 1
                page_header = f"\n\n## 第 {page_num} 页\n\n"
                all_markdown.append(page_header + page_text)
            
            # 合并所有页面的Markdown内容
            final_markdown = "\n".join(all_markdown)
            processing_time = time.time() - start_time
            
            # 清理临时文件
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
            
            # 更新任务状态为完成
            tasks[task_id] = {
                "status": "completed", 
                "markdown": final_markdown, 
                "error": None,
                "total_pages": total_pages,
                "processed_pages": processed_pages,
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
            
            # 清理临时文件
            temp_pdf_path = f"/tmp/temp_{task_id}.pdf"
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)


@app.on_event("startup")
async def startup_event():
    """启动时加载模型和初始化资源"""
    global predictors, task_semaphore, thread_pool, load_pdf, CLILoader, settings
    
    # 加载Surya模块
    load_predictors, load_pdf_func, CLILoader_class, settings_module = load_surya_modules()
    load_pdf = load_pdf_func
    CLILoader = CLILoader_class
    settings = settings_module
    
    # 加载模型
    print("🔄 正在加载Surya模型...")
    predictors = load_predictors()
    print("✅ Surya模型加载完成")
    
    # 创建默认 API 密钥
    default_key = generate_api_key("default")
    print(f"\n🔑 默认 API 密钥: {default_key}\n")
    
    # 初始化信号量用于限制并发任务数
    task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    print(f"📊 最大并发任务数: {MAX_CONCURRENT_TASKS}")
    
    # 初始化线程池
    thread_pool = ThreadPoolExecutor(max_workers=min(32, os.cpu_count() + 4))
    
    # 打印配置信息
    print(f"🖥️  设备: {settings.TORCH_DEVICE_MODEL}")
    print(f"📐 图像DPI: {settings.IMAGE_DPI}")
    print(f"📐 高分辨率DPI: {settings.IMAGE_DPI_HIGHRES}")


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
    max_pages: Optional[int] = Query(None, description="最大处理页数，从第一页开始"),
    page_range: Optional[str] = Query(None, description="页面范围，如'0,5-10,20'"),
    enable_math: bool = Query(True, description="是否启用数学公式识别"),
    api_key: str = Depends(get_api_key),
):
    """
    将PDF文件转换为Markdown格式（支持原生page_range和max_pages）
    
    - **file**: PDF文件
    - **max_pages**: 最大处理页数，从第一页开始，None表示处理所有页面
    - **page_range**: 页面范围，如'0,5-10,20'，优先级高于max_pages
    - **enable_math**: 是否启用数学公式识别
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    # 检查文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 检查参数冲突
    if page_range and max_pages:
        raise HTTPException(status_code=400, detail="page_range和max_pages不能同时指定")
    
    # 读取文件内容
    pdf_bytes = await file.read()
    
    # 生成任务ID
    task_id = f"task_{int(time.time() * 1000)}_{len(tasks)}"
    
    # 在后台异步处理PDF
    background_tasks.add_task(
        process_pdf_native, 
        task_id, 
        pdf_bytes, 
        max_pages,
        page_range,
        enable_math
    )
    
    return ConversionResult(task_id=task_id, status="processing")


@app.post("/convert-url", response_model=ConversionResult)
async def convert_pdf_from_url(
    request: ConvertRequest,
    api_key: str = Depends(get_api_key),
):
    """
    通过URL下载PDF文件并转换为Markdown格式
    
    - **url**: PDF文件的URL
    - **max_pages**: 最大处理页数，从第一页开始
    - **page_range**: 页面范围，如'0,5-10,20'
    - **enable_math**: 是否启用数学公式识别
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="必须提供PDF文件URL")
    
    # 检查参数冲突
    if request.page_range and request.max_pages:
        raise HTTPException(status_code=400, detail="page_range和max_pages不能同时指定")
    
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
        
        # 生成任务ID
        task_id = f"task_{int(time.time() * 1000)}_{len(tasks)}"
        
        # 在后台异步处理PDF
        asyncio.create_task(process_pdf_native(
            task_id, 
            pdf_bytes, 
            request.max_pages,
            request.page_range,
            request.enable_math
        ))
        
        return ConversionResult(task_id=task_id, status="processing")
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"下载PDF文件失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理PDF文件时出错: {str(e)}")


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
        "device": settings.TORCH_DEVICE_MODEL if settings else "unknown",
        "active_tasks": len([t for t in tasks.values() if t.get("status") == "processing"]),
        "total_tasks": len(tasks),
        "surya_version": "native",
        "features": {
            "page_range": True,
            "max_pages": True,
            "math_support": True
        }
    }


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="xDAN Smart API - 基于Surya原生功能")
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="API 服务端口号（默认：8080）"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="127.0.0.1", 
        help="API 服务主机地址（默认：127.0.0.1）"
    )
    parser.add_argument(
        "--max-concurrent", 
        type=int, 
        default=3, 
        help="最大并发任务数（默认：3）"
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
    
    print("🚀 启动基于Surya原生功能的API服务")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"📖 API文档: http://{args.host}:{args.port}/docs")
    print(f"⚡ 最大并发: {args.max_concurrent}")
    print()
    
    # 启动服务
    uvicorn.run(
        "pdf_to_markdown_api_native:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload
    ) 