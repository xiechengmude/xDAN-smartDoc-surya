#!/usr/bin/env python3
"""
Surya OCR API 主入口文件
支持PDF转Markdown的API服务 - 优化版本
"""

import sys
import os

# 添加api目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

if __name__ == "__main__":
    # 直接运行优化版API
    import argparse
    import uvicorn
    from pdf_to_markdown_api import app, parse_arguments
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 启动服务
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port, 
        reload=args.reload
    )
