#!/usr/bin/env python3
"""
简单的API启动脚本
避免Python版本兼容性问题
"""

import argparse
import os
import sys

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    return True

def check_dependencies():
    """检查必要的依赖"""
    required_packages = [
        "fastapi", "uvicorn", "pypdfium2", "pydantic", "requests"
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

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动xDAN Smart API服务")
    parser.add_argument("--port", type=int, default=8080, help="端口号")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="主机地址")
    parser.add_argument("--max-concurrent", type=int, default=3, help="最大并发数")
    
    args = parser.parse_args()
    
    print("🔍 检查系统环境...")
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    print("✅ 环境检查通过")
    print()
    
    # 设置环境变量
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    
    # 启动API服务
    print(f"🚀 启动API服务...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   最大并发: {args.max_concurrent}")
    print(f"   API文档: http://{args.host}:{args.port}/docs")
    print()
    
    try:
        import uvicorn
        uvicorn.run(
            "pdf_to_markdown_api_simple:app",
            host=args.host,
            port=args.port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 