#!/usr/bin/env python3
"""
Surya OCR API 主入口文件
支持PDF转Markdown的API服务
"""

import sys
import os

# 添加api目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from pdf_to_markdown_api_simple import main

if __name__ == "__main__":
    main()
