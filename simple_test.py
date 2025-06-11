#!/usr/bin/env python3
"""
简化的远程API测试脚本
"""

import requests
import time

# 配置信息
API_BASE_URL = "http://159.54.182.15:8000"
API_KEY = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"

# 测试PDF
TEST_PDF = {
    "name": "澳门科技大学年度学术报告",
    "url": "https://www.must.edu.mo/images/RATO/publication/2008-annual-academic-report.pdf"
}

def simple_test():
    print("🚀 远程API简单测试")
    print(f"🌐 服务器: {API_BASE_URL}")
    print(f"📄 测试文件: {TEST_PDF['name']}")
    print("="*50)
    
    # 1. 提交转换任务
    print(f"📤 提交转换任务...")
    start_time = time.time()
    
    try:
        payload = {"url": TEST_PDF["url"]}
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        response = requests.post(f"{API_BASE_URL}/convert-url", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            submit_time = time.time() - start_time
            print(f"✅ 任务提交成功: {task_id} (耗时: {submit_time:.2f}s)")
        else:
            print(f"❌ 任务提交失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return
    except Exception as e:
        print(f"❌ 任务提交异常: {e}")
        return
    
    # 2. 等待处理完成
    print(f"⏳ 等待处理完成...")
    start_wait = time.time()
    
    while True:
        try:
            response = requests.get(f"{API_BASE_URL}/status/{task_id}", headers={"X-API-Key": API_KEY}, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                
                if status == "processing":
                    elapsed = time.time() - start_wait
                    print(f"🔄 处理中... (已等待: {elapsed:.1f}s)")
                elif status == "completed":
                    total_time = time.time() - start_wait
                    markdown = result.get("markdown", "")
                    
                    print(f"\n🎉 处理完成!")
                    print(f"📊 结果统计:")
                    print(f"   总等待时间: {total_time:.2f}s")
                    print(f"   Markdown长度: {len(markdown):,} 字符")
                    
                    # 简单分析Markdown内容
                    if markdown:
                        lines = markdown.split('\n')
                        non_empty_lines = [line for line in lines if line.strip()]
                        print(f"   有效行数: {len(non_empty_lines)}")
                        
                        # 估算页数（通过"第 X 页"标记）
                        page_markers = [line for line in lines if "第" in line and "页" in line]
                        if page_markers:
                            print(f"   检测到页面数: {len(page_markers)}")
                            if len(page_markers) > 0:
                                avg_time_per_page = total_time / len(page_markers)
                                print(f"   平均每页处理时间: {avg_time_per_page:.2f}s")
                                print(f"   处理速度: {len(page_markers)/total_time:.2f} 页/秒")
                    
                    # 显示部分内容
                    if len(markdown) > 200:
                        print(f"\n📝 内容预览 (前200字符):")
                        print(markdown[:200] + "...")
                    
                    break
                elif status == "failed":
                    error = result.get("error", "未知错误")
                    print(f"❌ 处理失败: {error}")
                    break
            else:
                print(f"❌ 状态查询失败: {response.status_code}")
                break
            
            time.sleep(3)  # 每3秒检查一次
            
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            time.sleep(5)
    
    print(f"\n🏁 测试完成!")

if __name__ == "__main__":
    simple_test() 