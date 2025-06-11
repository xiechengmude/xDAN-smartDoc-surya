#!/usr/bin/env python3
"""
xDAN Smart API 使用示例
展示新功能的使用方法
"""

import asyncio
import aiohttp
import json
import time

# API配置
API_BASE_URL = "http://127.0.0.1:8080"
API_KEY = "your_api_key_here"  # 替换为实际的API密钥

async def example_page_range_conversion():
    """示例：页面范围转换"""
    print("📄 示例1: 页面范围转换")
    
    # 示例PDF URL
    pdf_url = "https://arxiv.org/pdf/2301.13688.pdf"
    
    request_data = {
        "url": pdf_url,
        "page_range": "0-2",  # 只处理前3页
        "enable_math": True,
        "task_name": "ocr_with_boxes"
    }
    
    async with aiohttp.ClientSession() as session:
        # 提交转换任务
        async with session.post(
            f"{API_BASE_URL}/convert-url",
            json=request_data,
            headers={"X-API-Key": API_KEY}
        ) as response:
            result = await response.json()
            task_id = result["task_id"]
            print(f"✅ 任务已提交: {task_id}")
            
            # 等待完成
            while True:
                async with session.get(
                    f"{API_BASE_URL}/status/{task_id}",
                    headers={"X-API-Key": API_KEY}
                ) as status_response:
                    status_result = await status_response.json()
                    
                    if status_result["status"] == "completed":
                        print(f"✅ 转换完成，处理时间: {status_result['processing_time']:.2f}秒")
                        print(f"📊 总页数: {status_result['total_pages']}")
                        print(f"📄 处理页面: {len(status_result['processed_pages'])}页")
                        break
                    elif status_result["status"] == "failed":
                        print(f"❌ 转换失败: {status_result['error']}")
                        break
                    else:
                        print("⏳ 处理中...")
                        await asyncio.sleep(2)

async def example_batch_conversion():
    """示例：批量转换"""
    print("\n📚 示例2: 批量转换")
    
    request_data = {
        "urls": [
            "https://arxiv.org/pdf/2301.13688.pdf",
            "https://arxiv.org/pdf/2301.13688.pdf"  # 使用相同URL作为示例
        ],
        "page_range": "0",  # 每个文档只处理第一页
        "enable_math": True,
        "task_name": "ocr_with_boxes"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE_URL}/convert-batch",
            json=request_data,
            headers={"X-API-Key": API_KEY}
        ) as response:
            result = await response.json()
            task_id = result["task_id"]
            print(f"✅ 批量任务已提交: {task_id}")
            
            # 监控进度
            while True:
                async with session.get(
                    f"{API_BASE_URL}/status/{task_id}",
                    headers={"X-API-Key": API_KEY}
                ) as status_response:
                    status_result = await status_response.json()
                    
                    if status_result["status"] == "completed":
                        print(f"✅ 批量转换完成，处理时间: {status_result['processing_time']:.2f}秒")
                        break
                    elif status_result["status"] == "failed":
                        print(f"❌ 批量转换失败: {status_result['error']}")
                        break
                    else:
                        print("⏳ 批量处理中...")
                        await asyncio.sleep(3)

async def example_different_task_types():
    """示例：不同OCR任务类型对比"""
    print("\n🔄 示例3: 不同OCR任务类型对比")
    
    pdf_url = "https://arxiv.org/pdf/2301.13688.pdf"
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
            
            start_time = time.time()
            
            async with session.post(
                f"{API_BASE_URL}/convert-url",
                json=request_data,
                headers={"X-API-Key": API_KEY}
            ) as response:
                result = await response.json()
                task_id = result["task_id"]
                
                # 等待完成
                while True:
                    async with session.get(
                        f"{API_BASE_URL}/status/{task_id}",
                        headers={"X-API-Key": API_KEY}
                    ) as status_response:
                        status_result = await status_response.json()
                        
                        if status_result["status"] == "completed":
                            end_time = time.time()
                            results[task_type] = {
                                "processing_time": status_result["processing_time"],
                                "total_time": end_time - start_time,
                                "text_length": len(status_result["markdown"])
                            }
                            print(f"    ✅ 完成，处理时间: {status_result['processing_time']:.2f}秒")
                            break
                        elif status_result["status"] == "failed":
                            print(f"    ❌ 失败: {status_result['error']}")
                            break
                        else:
                            await asyncio.sleep(1)
    
    # 显示对比结果
    print("\n📊 性能对比结果:")
    for task_type, metrics in results.items():
        print(f"  {task_type}:")
        print(f"    处理时间: {metrics['processing_time']:.2f}秒")
        print(f"    总时间: {metrics['total_time']:.2f}秒")
        print(f"    文本长度: {metrics['text_length']} 字符")

async def example_task_management():
    """示例：任务管理"""
    print("\n📋 示例4: 任务管理")
    
    async with aiohttp.ClientSession() as session:
        # 列出所有任务
        async with session.get(
            f"{API_BASE_URL}/tasks",
            headers={"X-API-Key": API_KEY}
        ) as response:
            tasks = await response.json()
            print(f"📝 当前任务总数: {len(tasks)}")
            
            # 按状态分组显示
            status_counts = {}
            for task_id, task_info in tasks.items():
                status = task_info.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                print(f"  {status}: {count} 个任务")
        
        # 检查健康状态
        async with session.get(f"{API_BASE_URL}/health") as response:
            health = await response.json()
            print(f"\n🏥 服务健康状态:")
            print(f"  状态: {health['status']}")
            print(f"  设备: {health['device']}")
            print(f"  活跃任务: {health['active_tasks']}")
            print(f"  总任务数: {health['total_tasks']}")

async def example_file_upload():
    """示例：文件上传转换"""
    print("\n📁 示例5: 文件上传转换")
    
    # 注意：这个示例需要一个实际的PDF文件
    # 如果没有文件，可以跳过这个示例
    
    pdf_file_path = "example.pdf"  # 替换为实际的PDF文件路径
    
    try:
        async with aiohttp.ClientSession() as session:
            # 准备文件上传
            data = aiohttp.FormData()
            data.add_field('file', 
                          open(pdf_file_path, 'rb'),
                          filename='example.pdf',
                          content_type='application/pdf')
            
            # 添加查询参数
            params = {
                'page_range': '0-2',
                'enable_math': 'true',
                'task_name': 'ocr_with_boxes'
            }
            
            async with session.post(
                f"{API_BASE_URL}/convert",
                data=data,
                params=params,
                headers={"X-API-Key": API_KEY}
            ) as response:
                result = await response.json()
                task_id = result["task_id"]
                print(f"✅ 文件上传任务已提交: {task_id}")
                
                # 等待完成
                while True:
                    async with session.get(
                        f"{API_BASE_URL}/status/{task_id}",
                        headers={"X-API-Key": API_KEY}
                    ) as status_response:
                        status_result = await status_response.json()
                        
                        if status_result["status"] == "completed":
                            print(f"✅ 文件转换完成，处理时间: {status_result['processing_time']:.2f}秒")
                            break
                        elif status_result["status"] == "failed":
                            print(f"❌ 文件转换失败: {status_result['error']}")
                            break
                        else:
                            print("⏳ 文件处理中...")
                            await asyncio.sleep(2)
                            
    except FileNotFoundError:
        print("⚠️ 未找到示例PDF文件，跳过文件上传测试")
    except Exception as e:
        print(f"❌ 文件上传测试失败: {e}")

async def main():
    """主函数"""
    print("🚀 xDAN Smart API 使用示例")
    print("=" * 50)
    
    try:
        # 运行各种示例
        await example_page_range_conversion()
        await example_batch_conversion()
        await example_different_task_types()
        await example_task_management()
        await example_file_upload()
        
        print("\n🎉 所有示例运行完成！")
        
    except aiohttp.ClientError as e:
        print(f"❌ 网络连接错误: {e}")
        print("请确保API服务正在运行")
    except Exception as e:
        print(f"❌ 运行示例时出错: {e}")

if __name__ == "__main__":
    # 运行示例
    print("💡 使用提示:")
    print("1. 确保API服务正在运行 (python start_optimized_api.py)")
    print("2. 替换 API_KEY 为实际的API密钥")
    print("3. 根据需要修改PDF URL或文件路径")
    print()
    
    asyncio.run(main()) 