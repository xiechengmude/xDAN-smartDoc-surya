#!/usr/bin/env python3
"""
xDAN Smart API 快速开始脚本
最简单的使用方式
"""

import requests
import time

def convert_pdf(pdf_url):
    """一键转换PDF为Markdown"""
    
    # API配置
    API_URL = "http://159.54.182.15:8000"
    API_KEY = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"
    
    print(f"🚀 开始转换: {pdf_url}")
    
    # 1. 提交任务
    response = requests.post(
        f"{API_URL}/convert-url",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={"url": pdf_url}
    )
    
    if response.status_code != 200:
        print(f"❌ 提交失败: {response.status_code}")
        return None
    
    task_id = response.json()["task_id"]
    print(f"✅ 任务ID: {task_id}")
    
    # 2. 等待完成
    while True:
        response = requests.get(
            f"{API_URL}/status/{task_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result["status"]
            
            if status == "processing":
                print("🔄 处理中...")
            elif status == "completed":
                print("✅ 转换完成!")
                return result["markdown"]
            elif status == "failed":
                print(f"❌ 转换失败: {result.get('error')}")
                return None
        
        time.sleep(3)

if __name__ == "__main__":
    # 使用示例
    pdf_url = "https://www.cbd.int/doc/c/d851/4e37/449bb1fdb754412f1ab5d9c5/cop-14-l-06-zh.pdf"
    
    markdown = convert_pdf(pdf_url)
    
    if markdown:
        # 保存结果
        with open("output.md", "w", encoding="utf-8") as f:
            f.write(markdown)
        
        print(f"📄 已保存到: output.md")
        print(f"📊 内容长度: {len(markdown):,} 字符")
        
        # 显示预览
        if len(markdown) > 200:
            print(f"\n📝 内容预览:")
            print("-" * 40)
            print(markdown[:200] + "...")
    else:
        print("❌ 转换失败") 