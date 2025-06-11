#!/usr/bin/env python3
"""
优化的PDF转Markdown API启动脚本
自动检测硬件配置并应用最佳性能设置
"""

import argparse
import os
import sys
import uvicorn
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_dependencies():
    """检查必要的依赖"""
    required_packages = [
        "torch", "fastapi", "uvicorn", "pypdfium2", 
        "pydantic", "aiohttp", "psutil"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少必要依赖: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def setup_environment():
    """设置环境变量和优化配置"""
    try:
        from surya_config import SuryaOptimizer
        
        print("🔧 正在分析硬件配置...")
        optimizer = SuryaOptimizer()
        optimizer.apply_optimizations()
        
        # 获取推荐的API设置
        api_settings = optimizer.get_recommended_api_settings()
        
        print("\n📊 性能优化摘要:")
        print(f"   设备: {optimizer.device}")
        print(f"   可用内存: {optimizer.available_memory/1024:.1f} GB")
        print(f"   推荐并发数: {api_settings['max_concurrent_tasks']}")
        print(f"   推荐批处理大小: {api_settings['default_batch_size']}")
        print(f"   线程池大小: {api_settings['thread_pool_workers']}")
        
        return api_settings
        
    except ImportError:
        print("⚠️ 未找到surya_config.py，使用默认配置")
        return {
            "max_concurrent_tasks": 5,
            "default_batch_size": 32,
            "thread_pool_workers": 16
        }

def validate_surya_installation():
    """验证Surya安装"""
    try:
        from surya.models import load_predictors
        from surya.settings import settings
        print(f"✅ Surya已正确安装，设备: {settings.TORCH_DEVICE_MODEL}")
        return True
    except ImportError as e:
        print(f"❌ Surya导入失败: {e}")
        print("请确保已正确安装Surya OCR")
        return False
    except Exception as e:
        print(f"❌ Surya配置错误: {e}")
        return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="优化的xDAN Smart API - PDF到Markdown转换服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python start_optimized_api.py                    # 使用默认设置启动
  python start_optimized_api.py --port 8080        # 指定端口
  python start_optimized_api.py --max-concurrent 8 # 指定最大并发数
  python start_optimized_api.py --auto-optimize    # 自动优化配置
  python start_optimized_api.py --dev              # 开发模式
        """
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="API服务端口号（默认：8080）"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="127.0.0.1", 
        help="API服务主机地址（默认：127.0.0.1）"
    )
    parser.add_argument(
        "--max-concurrent", 
        type=int, 
        help="最大并发任务数（默认：自动检测）"
    )
    parser.add_argument(
        "--auto-optimize", 
        action="store_true", 
        help="自动优化性能配置"
    )
    parser.add_argument(
        "--dev", 
        action="store_true", 
        help="开发模式（启用热重载）"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1, 
        help="Uvicorn工作进程数（默认：1）"
    )
    parser.add_argument(
        "--log-level", 
        choices=["debug", "info", "warning", "error"], 
        default="info", 
        help="日志级别（默认：info）"
    )
    parser.add_argument(
        "--check-only", 
        action="store_true", 
        help="仅检查配置，不启动服务"
    )
    
    return parser.parse_args()

def print_startup_info(args, api_settings):
    """打印启动信息"""
    print("\n" + "="*60)
    print("🚀 xDAN Smart API 启动信息")
    print("="*60)
    print(f"📡 服务地址: http://{args.host}:{args.port}")
    print(f"📋 API文档: http://{args.host}:{args.port}/docs")
    print(f"⚡ 最大并发: {args.max_concurrent or api_settings['max_concurrent_tasks']}")
    print(f"🔧 工作进程: {args.workers}")
    print(f"📝 日志级别: {args.log_level}")
    
    if args.dev:
        print("🛠️  开发模式: 已启用")
    
    print("\n💡 使用提示:")
    print("  - 使用 Ctrl+C 停止服务")
    print("  - 访问 /docs 查看API文档")
    print("  - 访问 /health 检查服务状态")
    print("="*60)

def main():
    """主函数"""
    args = parse_arguments()
    
    print("🔍 正在检查系统环境...")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 验证Surya安装
    if not validate_surya_installation():
        sys.exit(1)
    
    # 设置环境和优化配置
    if args.auto_optimize:
        api_settings = setup_environment()
    else:
        api_settings = {
            "max_concurrent_tasks": 5,
            "default_batch_size": 32,
            "thread_pool_workers": 16
        }
    
    # 应用命令行参数覆盖
    if args.max_concurrent:
        api_settings["max_concurrent_tasks"] = args.max_concurrent
        os.environ["MAX_CONCURRENT_TASKS"] = str(args.max_concurrent)
    
    # 仅检查配置模式
    if args.check_only:
        print("\n✅ 配置检查完成，所有依赖正常")
        return
    
    # 打印启动信息
    print_startup_info(args, api_settings)
    
    try:
        # 启动API服务
        uvicorn.run(
            "pdf_to_markdown_api:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level=args.log_level,
            reload=args.dev,
            access_log=True,
            # 性能优化设置
            loop="uvloop" if not args.dev else "asyncio",
            http="httptools" if not args.dev else "h11",
            # 限制请求大小（100MB）
            limit_max_requests=1000,
            timeout_keep_alive=5,
        )
        
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 