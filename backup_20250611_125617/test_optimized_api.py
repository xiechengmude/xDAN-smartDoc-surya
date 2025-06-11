#!/usr/bin/env python3
"""
测试优化后的PDF转Markdown API服务
包含page_range、批处理、异步处理等新功能的测试
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any
import argparse


class APITester:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    async def test_health_check(self) -> Dict[str, Any]:
        """测试健康检查端点"""
        print("🔍 测试健康检查...")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                result = await response.json()
                print(f"✅ 健康检查结果: {result}")
                return result
    
    async def test_page_range_conversion(self, pdf_url: str, page_range: str) -> str:
        """测试页面范围转换功能"""
        print(f"📄 测试页面范围转换: {page_range}")
        
        request_data = {
            "url": pdf_url,
            "page_range": page_range,
            "enable_math": True,
            "task_name": "ocr_with_boxes"
        }
        
        async with aiohttp.ClientSession() as session:
            # 提交转换任务
            async with session.post(
                f"{self.base_url}/convert-url",
                json=request_data,
                headers=self.headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ 提交任务失败: {error_text}")
                    return None
                
                result = await response.json()
                task_id = result["task_id"]
                print(f"✅ 任务已提交: {task_id}")
                
                # 轮询任务状态
                return await self.wait_for_completion(session, task_id)
    
    async def test_batch_conversion(self, pdf_urls: List[str], page_range: str = None) -> str:
        """测试批量转换功能"""
        print(f"📚 测试批量转换: {len(pdf_urls)} 个文件")
        
        request_data = {
            "urls": pdf_urls,
            "page_range": page_range,
            "enable_math": True,
            "task_name": "ocr_with_boxes"
        }
        
        async with aiohttp.ClientSession() as session:
            # 提交批量转换任务
            async with session.post(
                f"{self.base_url}/convert-batch",
                json=request_data,
                headers=self.headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ 提交批量任务失败: {error_text}")
                    return None
                
                result = await response.json()
                task_id = result["task_id"]
                print(f"✅ 批量任务已提交: {task_id}")
                
                # 轮询任务状态
                return await self.wait_for_completion(session, task_id)
    
    async def test_different_task_types(self, pdf_url: str) -> Dict[str, str]:
        """测试不同的OCR任务类型"""
        print("🔄 测试不同OCR任务类型...")
        
        task_types = ["ocr_with_boxes", "ocr_without_boxes", "block_without_boxes"]
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for task_type in task_types:
                print(f"  测试任务类型: {task_type}")
                
                request_data = {
                    "url": pdf_url,
                    "page_range": "0",  # 只处理第一页
                    "enable_math": True,
                    "task_name": task_type
                }
                
                async with session.post(
                    f"{self.base_url}/convert-url",
                    json=request_data,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        task_id = result["task_id"]
                        completion_result = await self.wait_for_completion(session, task_id)
                        results[task_type] = completion_result
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {task_type} 失败: {error_text}")
                        results[task_type] = None
        
        return results
    
    async def test_concurrent_requests(self, pdf_url: str, num_requests: int = 3) -> List[str]:
        """测试并发请求处理"""
        print(f"⚡ 测试并发处理: {num_requests} 个并发请求")
        
        async def submit_single_request(session, request_id):
            request_data = {
                "url": pdf_url,
                "page_range": f"{request_id}",  # 每个请求处理不同页面
                "enable_math": True,
                "task_name": "ocr_with_boxes"
            }
            
            async with session.post(
                f"{self.base_url}/convert-url",
                json=request_data,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_id = result["task_id"]
                    print(f"  ✅ 请求 {request_id} 已提交: {task_id}")
                    return await self.wait_for_completion(session, task_id)
                else:
                    error_text = await response.text()
                    print(f"  ❌ 请求 {request_id} 失败: {error_text}")
                    return None
        
        async with aiohttp.ClientSession() as session:
            # 并发提交多个请求
            tasks = [
                submit_single_request(session, i) 
                for i in range(num_requests)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            print(f"✅ 并发测试完成，耗时: {end_time - start_time:.2f} 秒")
            return results
    
    async def wait_for_completion(self, session: aiohttp.ClientSession, task_id: str, timeout: int = 300) -> str:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            async with session.get(
                f"{self.base_url}/status/{task_id}",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    print(f"❌ 获取任务状态失败: {await response.text()}")
                    return None
                
                result = await response.json()
                status = result["status"]
                
                if status == "completed":
                    processing_time = result.get("processing_time", 0)
                    total_pages = result.get("total_pages", 0)
                    processed_pages = result.get("processed_pages", [])
                    
                    print(f"✅ 任务完成: {task_id}")
                    print(f"   处理时间: {processing_time:.2f} 秒")
                    print(f"   总页数: {total_pages}")
                    print(f"   处理页面: {len(processed_pages)} 页")
                    
                    return result["markdown"]
                
                elif status == "failed":
                    error = result.get("error", "未知错误")
                    print(f"❌ 任务失败: {task_id}, 错误: {error}")
                    return None
                
                elif status == "processing":
                    processed_pages = result.get("processed_pages", [])
                    if processed_pages:
                        print(f"⏳ 任务处理中: {task_id}, 已处理 {len(processed_pages)} 页")
                    else:
                        print(f"⏳ 任务处理中: {task_id}")
                
                # 等待一段时间后再次检查
                await asyncio.sleep(2)
        
        print(f"⏰ 任务超时: {task_id}")
        return None
    
    async def test_task_management(self) -> None:
        """测试任务管理功能"""
        print("📋 测试任务管理功能...")
        
        async with aiohttp.ClientSession() as session:
            # 列出所有任务
            async with session.get(
                f"{self.base_url}/tasks",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    tasks = await response.json()
                    print(f"✅ 当前任务数: {len(tasks)}")
                    
                    # 列出处理中的任务
                    async with session.get(
                        f"{self.base_url}/tasks?status=processing",
                        headers=self.headers
                    ) as response:
                        if response.status == 200:
                            processing_tasks = await response.json()
                            print(f"✅ 处理中任务数: {len(processing_tasks)}")
                else:
                    print(f"❌ 获取任务列表失败: {await response.text()}")


async def main():
    parser = argparse.ArgumentParser(description="测试优化后的PDF转Markdown API")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="API服务地址")
    parser.add_argument("--api-key", help="API密钥")
    parser.add_argument("--pdf-url", help="测试用的PDF文件URL")
    parser.add_argument("--test-type", choices=["all", "health", "page-range", "batch", "concurrent", "task-types"], 
                       default="all", help="测试类型")
    
    args = parser.parse_args()
    
    # 默认测试PDF URL（可以替换为你自己的PDF文件）
    default_pdf_url = "https://arxiv.org/pdf/2301.13688.pdf"  # 一个示例学术论文
    pdf_url = args.pdf_url or default_pdf_url
    
    tester = APITester(args.url, args.api_key)
    
    print(f"🚀 开始测试API服务: {args.url}")
    print(f"📄 测试PDF: {pdf_url}")
    print("=" * 60)
    
    try:
        if args.test_type in ["all", "health"]:
            await tester.test_health_check()
            print()
        
        if args.test_type in ["all", "page-range"]:
            # 测试页面范围功能
            print("测试1: 单页转换")
            await tester.test_page_range_conversion(pdf_url, "0")
            print()
            
            print("测试2: 多页范围转换")
            await tester.test_page_range_conversion(pdf_url, "0-2")
            print()
            
            print("测试3: 不连续页面转换")
            await tester.test_page_range_conversion(pdf_url, "0,2,4")
            print()
        
        if args.test_type in ["all", "batch"]:
            # 测试批量转换
            print("测试4: 批量转换")
            batch_urls = [pdf_url, pdf_url]  # 使用相同URL进行测试
            await tester.test_batch_conversion(batch_urls, "0-1")
            print()
        
        if args.test_type in ["all", "task-types"]:
            # 测试不同任务类型
            print("测试5: 不同OCR任务类型")
            await tester.test_different_task_types(pdf_url)
            print()
        
        if args.test_type in ["all", "concurrent"]:
            # 测试并发处理
            print("测试6: 并发请求处理")
            await tester.test_concurrent_requests(pdf_url, 3)
            print()
        
        # 测试任务管理
        await tester.test_task_management()
        
        print("=" * 60)
        print("🎉 所有测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 