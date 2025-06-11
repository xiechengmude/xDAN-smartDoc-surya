#!/usr/bin/env python3
"""
单个PDF测试脚本
"""

import requests
import time

# API配置
API_BASE_URL = "http://localhost:8090"

# 测试PDF URL
TEST_URL = "https://www.cast.org.cn/cms_files/filemanager/583933374/attach/20235/c8003514d41a4625a0d36b3c9dbd7ae3.pdf"

def test_api():
    print("🚀 测试远程GPU API服务")
    print(f"API地址: {API_BASE_URL}")
    print("=" * 50)
    
    # 测试健康状态
    print("🔍 测试API健康状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API服务正常运行")
            print(f"   状态: {data.get('status')}")
            print(f"   设备: {data.get('device')}")
            print(f"   活跃任务: {data.get('active_tasks')}")
        else:
            print(f"❌ API健康检查失败: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ API连接失败: {e}")
        return
    
    # 下载PDF
    print(f"\n📥 下载测试PDF...")
    print(f"URL: {TEST_URL}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(TEST_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        pdf_filename = "test_pdf.pdf"
        with open(pdf_filename, 'wb') as f:
            f.write(response.content)
        
        file_size = len(response.content) / 1024 / 1024
        print(f"✅ 下载完成: {pdf_filename} ({file_size:.2f} MB)")
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return
    
    # 转换PDF
    print(f"\n🔄 转换PDF为Markdown...")
    
    try:
        with open(pdf_filename, 'rb') as f:
            files = {'file': (pdf_filename, f, 'application/pdf')}
            data = {
                'max_pages': 3,
                'task_type': 'ocr_without_boxes'
            }
            
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/convert",
                files=files,
                data=data,
                timeout=300
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                processing_time = end_time - start_time
                
                print("✅ 转换成功！")
                print(f"   处理时间: {processing_time:.2f}秒")
                print(f"   页面数量: {result.get('page_count', 'unknown')}")
                print(f"   输出长度: {len(result.get('markdown', ''))}")
                
                # 保存结果
                output_file = f"test_result_{int(time.time())}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# PDF转换测试结果\n\n")
                    f.write(f"**原始URL**: {TEST_URL}\n")
                    f.write(f"**处理时间**: {processing_time:.2f}秒\n")
                    f.write(f"**页面数量**: {result.get('page_count')}\n")
                    f.write(f"**转换时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(result.get('markdown', ''))
                
                print(f"💾 结果已保存: {output_file}")
                
            else:
                print(f"❌ 转换失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                
    except Exception as e:
        print(f"❌ 转换异常: {e}")
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    test_api() 