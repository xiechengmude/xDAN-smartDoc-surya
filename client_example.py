#!/usr/bin/env python3
"""
xDAN Smart API 客户端使用示例
完整的PDF转Markdown转换客户端
"""

import requests
import time
import os
from typing import Optional

class XDANSmartClient:
    """xDAN Smart API 客户端"""
    
    def __init__(self, base_url: str = "http://159.54.182.15:8000", api_key: str = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
    
    def convert_from_url(self, pdf_url: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        通过URL转换PDF为Markdown
        
        Args:
            pdf_url: PDF文件的URL
            output_file: 输出文件路径（可选）
            
        Returns:
            转换后的Markdown内容，失败返回None
        """
        print(f"🚀 开始转换PDF: {pdf_url}")
        
        # 1. 提交转换任务
        payload = {"url": pdf_url}
        headers = {**self.headers, "Content-Type": "application/json"}
        
        try:
            response = requests.post(f"{self.base_url}/convert-url", headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ 任务提交失败: HTTP {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
            
            result = response.json()
            task_id = result.get("task_id")
            print(f"✅ 任务提交成功: {task_id}")
            
        except Exception as e:
            print(f"❌ 任务提交异常: {e}")
            return None
        
        # 2. 等待处理完成
        return self._wait_for_completion(task_id, output_file)
    
    def convert_from_file(self, file_path: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        上传本地PDF文件进行转换
        
        Args:
            file_path: 本地PDF文件路径
            output_file: 输出文件路径（可选）
            
        Returns:
            转换后的Markdown内容，失败返回None
        """
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return None
        
        print(f"📤 上传文件: {file_path}")
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(f"{self.base_url}/convert", headers=self.headers, files=files, timeout=60)
            
            if response.status_code != 200:
                print(f"❌ 文件上传失败: HTTP {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
            
            result = response.json()
            task_id = result.get("task_id")
            print(f"✅ 文件上传成功: {task_id}")
            
        except Exception as e:
            print(f"❌ 文件上传异常: {e}")
            return None
        
        # 等待处理完成
        return self._wait_for_completion(task_id, output_file)
    
    def _wait_for_completion(self, task_id: str, output_file: Optional[str] = None) -> Optional[str]:
        """等待任务完成"""
        print(f"⏳ 等待处理完成...")
        start_time = time.time()
        
        while True:
            try:
                response = requests.get(f"{self.base_url}/status/{task_id}", headers=self.headers, timeout=10)
                
                if response.status_code != 200:
                    print(f"❌ 状态查询失败: HTTP {response.status_code}")
                    return None
                
                result = response.json()
                status = result.get("status")
                elapsed = time.time() - start_time
                
                if status == "processing":
                    print(f"🔄 处理中... (已等待: {elapsed:.1f}s)")
                elif status == "completed":
                    markdown = result.get("markdown", "")
                    print(f"✅ 转换完成! (总耗时: {elapsed:.1f}s)")
                    
                    # 分析结果
                    self._analyze_result(markdown)
                    
                    # 保存文件
                    if output_file:
                        self._save_to_file(markdown, output_file)
                    
                    return markdown
                    
                elif status == "failed":
                    error = result.get("error", "未知错误")
                    print(f"❌ 转换失败: {error}")
                    return None
                
                time.sleep(3)  # 每3秒检查一次
                
            except Exception as e:
                print(f"❌ 状态查询异常: {e}")
                time.sleep(5)
    
    def _analyze_result(self, markdown: str):
        """分析转换结果"""
        if not markdown:
            return
        
        lines = markdown.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        page_markers = [line for line in lines if "第" in line and "页" in line]
        
        print(f"📊 转换结果分析:")
        print(f"   总字符数: {len(markdown):,}")
        print(f"   有效行数: {len(non_empty_lines):,}")
        print(f"   检测页数: {len(page_markers)}")
        
        if len(markdown) > 500:
            print(f"📝 内容预览 (前500字符):")
            print("-" * 50)
            print(markdown[:500] + "...")
            print("-" * 50)
    
    def _save_to_file(self, content: str, file_path: str):
        """保存内容到文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"💾 文件已保存: {file_path}")
        except Exception as e:
            print(f"❌ 文件保存失败: {e}")

def main():
    """主函数 - 使用示例"""
    print("🚀 xDAN Smart API 客户端示例")
    print("=" * 50)
    
    # 创建客户端
    client = XDANSmartClient()
    
    # 示例1: 通过URL转换PDF
    print("\n📋 示例1: 通过URL转换PDF")
    pdf_url = "https://www.cbd.int/doc/c/d851/4e37/449bb1fdb754412f1ab5d9c5/cop-14-l-06-zh.pdf"
    markdown_content = client.convert_from_url(pdf_url, "example_output.md")
    
    if markdown_content:
        print("✅ URL转换成功!")
    else:
        print("❌ URL转换失败!")
    
    # 示例2: 上传本地文件转换（如果有的话）
    print("\n📋 示例2: 上传本地文件转换")
    local_file = "test.pdf"  # 替换为实际的PDF文件路径
    
    if os.path.exists(local_file):
        markdown_content = client.convert_from_file(local_file, "local_output.md")
        if markdown_content:
            print("✅ 本地文件转换成功!")
        else:
            print("❌ 本地文件转换失败!")
    else:
        print(f"⚠️  本地文件不存在: {local_file}")
        print("   请将PDF文件重命名为 test.pdf 放在当前目录下进行测试")
    
    print("\n🎉 示例演示完成!")

if __name__ == "__main__":
    main() 