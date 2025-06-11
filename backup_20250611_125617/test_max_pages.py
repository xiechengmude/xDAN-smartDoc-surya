#!/usr/bin/env python3
"""
测试max_pages功能的简单脚本
"""

import asyncio
import aiohttp
import json
import time

# API配置
API_BASE_URL = "http://127.0.0.1:8080"
API_KEY = "your_api_key_here"  # 需要从API启动时获取

async def test_max_pages():
    """测试max_pages功能"""
    print("📄 测试max_pages功能")
    
    # 示例PDF URL
    pdf_url = "https://arxiv.org/pdf/2301.13688.pdf"
    
    # 测试不同的max_pages设置
    test_cases = [
        {"max_pages": 1, "description": "只处理第1页"},
        {"max_pages": 3, "description": "处理前3页"},
        {"max_pages": None, "description": "处理所有页面"}
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases):
            print(f"\n测试 {i+1}: {test_case['description']}")
            
            request_data = {
                "url": pdf_url,
                "max_pages": test_case["max_pages"],
                "enable_math": True,
                "task_name": "ocr_with_boxes"
            }
            
            try:
                # 提交转换任务
                async with session.post(
                    f"{API_BASE_URL}/convert-url",
                    json=request_data,
                    headers={"X-API-Key": API_KEY}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ 提交任务失败: {error_text}")
                        continue
                    
                    result = await response.json()
                    task_id = result["task_id"]
                    print(f"✅ 任务已提交: {task_id}")
                    
                    # 等待完成
                    start_time = time.time()
                    while True:
                        async with session.get(
                            f"{API_BASE_URL}/status/{task_id}",
                            headers={"X-API-Key": API_KEY}
                        ) as status_response:
                            if status_response.status != 200:
                                print(f"❌ 获取状态失败")
                                break
                            
                            status_result = await status_response.json()
                            
                            if status_result["status"] == "completed":
                                end_time = time.time()
                                print(f"✅ 转换完成")
                                print(f"   处理时间: {status_result.get('processing_time', 0):.2f}秒")
                                print(f"   总时间: {end_time - start_time:.2f}秒")
                                print(f"   总页数: {status_result.get('total_pages', 0)}")
                                print(f"   处理页数: {status_result.get('processed_pages', 0)}")
                                
                                # 显示部分内容
                                markdown = status_result.get("markdown", "")
                                if markdown:
                                    preview = markdown[:200] + "..." if len(markdown) > 200 else markdown
                                    print(f"   内容预览: {preview}")
                                break
                            elif status_result["status"] == "failed":
                                print(f"❌ 转换失败: {status_result.get('error', '未知错误')}")
                                break
                            else:
                                print("⏳ 处理中...")
                                await asyncio.sleep(2)
                                
                                # 超时检查
                                if time.time() - start_time > 60:
                                    print("⏰ 超时，停止等待")
                                    break
                    
            except Exception as e:
                print(f"❌ 测试失败: {e}")

async def test_health():
    """测试健康检查"""
    print("🏥 测试健康检查")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ 服务健康状态:")
                    print(f"   状态: {health.get('status', 'unknown')}")
                    print(f"   设备: {health.get('device', 'unknown')}")
                    print(f"   活跃任务: {health.get('active_tasks', 0)}")
                    print(f"   总任务数: {health.get('total_tasks', 0)}")
                    return True
                else:
                    print(f"❌ 健康检查失败，状态码: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False

async def main():
    """主函数"""
    print("🚀 测试max_pages功能")
    print("=" * 50)
    
    # 首先测试健康检查
    if not await test_health():
        print("❌ API服务不可用，请先启动服务")
        print("启动命令: python pdf_to_markdown_api_simple.py --port 8080")
        return
    
    print()
    
    # 测试max_pages功能
    await test_max_pages()
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    print("💡 使用提示:")
    print("1. 确保API服务正在运行")
    print("2. 从API启动日志中获取API密钥并更新API_KEY变量")
    print("3. 确保网络连接正常")
    print()
    
    asyncio.run(main()) 