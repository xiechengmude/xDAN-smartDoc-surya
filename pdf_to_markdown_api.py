import argparse
import asyncio
import io
import os
import re
import secrets
from typing import List, Optional, Dict
import requests

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

# 根据设备类型设置最优批处理大小
def set_optimal_batch_sizes():
    """根据设备类型和可用内存设置最优的批处理大小"""
    device = settings.TORCH_DEVICE_MODEL
    
    if device == "cuda":
        # GPU 优化设置 - 根据文档建议的最优值
        os.environ["RECOGNITION_BATCH_SIZE"] = "512"  # 20GB VRAM
        os.environ["DETECTOR_BATCH_SIZE"] = "36"      # 16GB VRAM  
        os.environ["LAYOUT_BATCH_SIZE"] = "32"        # 7GB VRAM
        os.environ["TABLE_REC_BATCH_SIZE"] = "64"     # 10GB VRAM
        
        # 启用模型编译以提升性能
        os.environ["COMPILE_ALL"] = "true"
        
        print(f"🚀 GPU 优化模式已启用 - 设备: {device}")
        print("📊 批处理大小: RECOGNITION=512, DETECTOR=36, LAYOUT=32, TABLE_REC=64")
        print("⚡ 模型编译已启用")
        
    elif device == "mps":
        # Apple Silicon 优化设置
        os.environ["RECOGNITION_BATCH_SIZE"] = "64"
        os.environ["DETECTOR_BATCH_SIZE"] = "8"
        os.environ["LAYOUT_BATCH_SIZE"] = "4"
        os.environ["TABLE_REC_BATCH_SIZE"] = "8"
        
        print(f"🍎 Apple Silicon 优化模式已启用 - 设备: {device}")
        print("📊 批处理大小: RECOGNITION=64, DETECTOR=8, LAYOUT=4, TABLE_REC=8")
        
    else:
        # CPU 优化设置
        os.environ["RECOGNITION_BATCH_SIZE"] = "32"
        os.environ["DETECTOR_BATCH_SIZE"] = "6"
        os.environ["LAYOUT_BATCH_SIZE"] = "4"
        os.environ["TABLE_REC_BATCH_SIZE"] = "8"
        
        print(f"💻 CPU 优化模式已启用 - 设备: {device}")
        print("📊 批处理大小: RECOGNITION=32, DETECTOR=6, LAYOUT=4, TABLE_REC=8")

# 在导入 surya 之前设置环境变量
set_optimal_batch_sizes()

app = FastAPI(
    title="xDAN Smart API",
    description="高性能异步的 PDF 到 Markdown 转换服务，基于 xDAN Smart OCR",
    version="1.0.0",
)

# 全局变量存储预加载的模型
predictors = None

# 全局变量存储任务状态
tasks = {}

# 动态调整并发数（根据设备性能）
def get_optimal_concurrent_tasks():
    """根据设备类型返回最优并发任务数"""
    device = settings.TORCH_DEVICE_MODEL
    if device == "cuda":
        return 10  # GPU 可以处理更多并发
    elif device == "mps":
        return 6   # Apple Silicon 中等并发
    else:
        return 3   # CPU 较少并发

MAX_CONCURRENT_TASKS = get_optimal_concurrent_tasks()

# 信号量用于限制并发任务数
task_semaphore = None

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


class UrlConvertRequest(BaseModel):
    url: str


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


async def process_pdf_batch(task_id: str, pdf_bytes: bytes):
    """优化的批量PDF处理函数"""
    async with task_semaphore:
        try:
            # 更新任务状态为处理中
            tasks[task_id] = {"status": "processing", "markdown": None, "error": None}
            
            # 使用pypdfium2加载PDF文件
            pdf = pypdfium2.PdfDocument(pdf_bytes)
            page_count = len(pdf)
            
            # 批量渲染所有页面图像
            print(f"📄 开始处理 {page_count} 页PDF文档 (任务ID: {task_id})")
            
            # 批量渲染页面图像
            all_images = []
            for page_index in range(page_count):
                page = pdf[page_index]
                pil_image = page.render().to_pil()
                all_images.append(pil_image)
            
            print(f"🖼️  已渲染 {len(all_images)} 页图像")
            
            # 批量OCR处理 - 这是关键优化点
            # 为每个图像提供一个任务名称
            task_names = [TaskNames.ocr_with_boxes] * len(all_images)
            batch_predictions = predictors["recognition"](
                all_images,
                task_names=task_names,
                det_predictor=predictors["detection"],
                highres_images=all_images,
                math_mode=True,
                return_words=True,
            )
            
            print(f"🔍 OCR 批量处理完成")
            
            # 处理OCR结果
            all_markdown = []
            for page_index, img_pred in enumerate(batch_predictions):
                # 提取文本行
                page_text = "\n\n".join([replace_fences(line.text) for line in img_pred.text_lines])
                
                # 添加页码标记
                page_header = f"\n\n## 第 {page_index + 1} 页\n\n"
                all_markdown.append(page_header + page_text)
            
            # 合并所有页面的Markdown内容
            final_markdown = "\n".join(all_markdown)
            
            # 更新任务状态为完成
            tasks[task_id] = {"status": "completed", "markdown": final_markdown, "error": None}
            
            print(f"✅ 任务完成 (ID: {task_id}) - 处理了 {page_count} 页")
            
        except Exception as e:
            # 如果处理过程中出现错误，更新任务状态为失败
            tasks[task_id] = {"status": "failed", "markdown": None, "error": str(e)}
            print(f"❌ 处理PDF时出错 (任务ID: {task_id}): {e}")


# 保持向后兼容的函数名
async def process_pdf(task_id: str, pdf_bytes: bytes):
    """向后兼容的函数名"""
    await process_pdf_batch(task_id, pdf_bytes)


@app.on_event("startup")
async def startup_event():
    """启动时加载模型"""
    global predictors, task_semaphore
    
    print("🚀 正在启动 xDAN Smart API...")
    print(f"🔧 设备类型: {settings.TORCH_DEVICE_MODEL}")
    print(f"⚙️  最大并发任务数: {MAX_CONCURRENT_TASKS}")
    
    # 加载预训练模型
    print("📦 正在加载 Surya 模型...")
    predictors = load_predictors()
    print("✅ 模型加载完成")
    
    # 创建默认 API 密钥
    default_key = generate_api_key("default")
    print(f"🔑 默认 API 密钥已生成: {default_key}")
    
    # 初始化信号量用于限制并发任务数
    task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    print("🎉 xDAN Smart API 启动完成！")


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
    # 检查文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 读取文件内容
    pdf_bytes = await file.read()
    
    # 生成任务ID
    task_id = f"task_{len(tasks) + 1}"
    
    # 初始化任务状态
    tasks[task_id] = {"status": "processing", "markdown": None, "error": None}
    
    # 在后台异步处理PDF - 使用优化的批量处理函数
    background_tasks.add_task(process_pdf_batch, task_id, pdf_bytes)
    
    return ConversionResult(task_id=task_id, status="processing")


@app.post("/convert-url", response_model=ConversionResult)
async def convert_pdf_from_url(
    request: UrlConvertRequest,
    api_key: str = Depends(get_api_key),
):
    """
    通过URL下载PDF文件并转换为Markdown格式
    
    - **url**: PDF文件的URL
    
    返回任务ID，可以用于检查转换状态和获取结果
    """
    try:
        # 下载PDF文件
        response = requests.get(request.url, stream=True, timeout=30)
        response.raise_for_status()  # 确保请求成功
        
        # 检查内容类型
        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type.lower() and not request.url.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="URL不指向PDF文件")
        
        # 读取文件内容
        pdf_bytes = response.content
        
        # 生成任务ID
        task_id = f"task_{len(tasks) + 1}"
        
        # 初始化任务状态
        tasks[task_id] = {"status": "processing", "markdown": None, "error": None}
        
        # 在后台异步处理PDF - 使用优化的批量处理函数
        asyncio.create_task(process_pdf_batch(task_id, pdf_bytes))
        
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
        status=result.get("status", "unknown")
    )
    
    if result.get("status") == "completed":
        response.markdown = result.get("markdown")
    elif result.get("status") == "failed":
        response.error = result.get("error")
    
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
        default=None, 
        help="最大并发任务数（默认：根据设备自动调整）"
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
    
    # 如果用户指定了并发数，则覆盖自动检测的值
    if args.max_concurrent is not None:
        MAX_CONCURRENT_TASKS = args.max_concurrent
        print(f"🔧 用户指定最大并发任务数: {MAX_CONCURRENT_TASKS}")
    
    # 启动服务
    print(f"🌐 启动服务: http://{args.host}:{args.port}")
    uvicorn.run(
        "pdf_to_markdown_api:app", 
        host=args.host, 
        port=args.port, 
        reload=args.reload
    )
