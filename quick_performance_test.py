#!/usr/bin/env python3
"""
快速性能测试脚本 - 测试单个PDF文件的处理性能
"""

import requests
import time

# 配置信息
API_BASE_URL = "http://159.54.182.15:8000"
API_KEY = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"

# 测试PDF (选择一个较大的文件)
TEST_PDF = {
    "name": "澳门科技大学年度学术报告",
    "url": "https://www.must.edu.mo/images/RATO/publication/2008-annual-academic-report.pdf"
}

def quick_test():
    print("🚀 快速性能测试开始")
    print(f"🌐 服务器: {API_BASE_URL}")
    print(f"📄 测试文件: {TEST_PDF['name']}")
    print("="*50)
    
    # 1. 检查API状态
    print("📊 检查API当前状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/performance", headers={"X-API-Key": API_KEY}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 设备类型: {data.get('device_type')}")
            print(f"✅ 最大并发: {data.get('max_concurrent_tasks')}")
            print(f"✅ 批处理大小: {data.get('batch_sizes')}")
        else:
            print(f"❌ API状态检查失败: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        return
    
    # 2. 提交转换任务
    print(f"\n📤 提交转换任务...")
    start_submit = time.time()
    try:
        payload = {"url": TEST_PDF["url"]}
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        response = requests.post(f"{API_BASE_URL}/convert-url", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            submit_time = time.time() - start_submit
            print(f"✅ 任务提交成功: {task_id} (耗时: {submit_time:.2f}s)")
        else:
            print(f"❌ 任务提交失败: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 任务提交异常: {e}")
        return
    
    # 3. 等待处理完成
    print(f"⏳ 等待处理完成...")
    start_wait = time.time()
    last_pages = 0
    
    while True:
        try:
            response = requests.get(f"{API_BASE_URL}/status/{task_id}", headers={"X-API-Key": API_KEY}, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                pages_processed = result.get("pages_processed", 0)
                
                if status == "processing":
                    if pages_processed != last_pages:
                        print(f"🔄 处理中... 已处理页面: {pages_processed}")
                        last_pages = pages_processed
                elif status == "completed":
                    wait_time = time.time() - start_wait
                    processing_time = result.get("processing_time", 0)
                    total_pages = result.get("pages_processed", 0)
                    markdown_length = len(result.get("markdown", ""))
                    
                    print(f"\n🎉 处理完成!")
                    print(f"📊 处理统计:")
                    print(f"   总等待时间: {wait_time:.2f}s")
                    print(f"   实际处理时间: {processing_time:.2f}s")
                    print(f"   处理页面数: {total_pages}")
                    print(f"   Markdown长度: {markdown_length:,} 字符")
                    if total_pages > 0:
                        print(f"   平均每页处理时间: {processing_time/total_pages:.3f}s")
                        print(f"   处理速度: {total_pages/processing_time:.2f} 页/秒")
                    
                    # 显示性能等级
                    if total_pages > 0:
                        pages_per_sec = total_pages / processing_time
                        if pages_per_sec > 2:
                            print(f"⚡ 性能等级: 优秀 ({pages_per_sec:.2f} 页/秒)")
                        elif pages_per_sec > 1:
                            print(f"✅ 性能等级: 良好 ({pages_per_sec:.2f} 页/秒)")
                        else:
                            print(f"⚠️  性能等级: 一般 ({pages_per_sec:.2f} 页/秒)")
                    
                    break
                elif status == "failed":
                    error = result.get("error", "未知错误")
                    print(f"❌ 处理失败: {error}")
                    break
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            time.sleep(5)
    
    # 4. 获取最终性能统计
    print(f"\n📈 获取最终性能统计...")
    try:
        response = requests.get(f"{API_BASE_URL}/performance", headers={"X-API-Key": API_KEY}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 服务器总统计:")
            print(f"   已处理文档: {data.get('total_processed')}")
            print(f"   已处理页面: {data.get('total_pages')}")
            print(f"   平均每页时间: {data.get('average_time_per_page', 0):.3f}s")
    except Exception as e:
        print(f"❌ 性能统计获取失败: {e}")
    
    print(f"\n🏁 快速测试完成!")

if __name__ == "__main__":
    quick_test() 