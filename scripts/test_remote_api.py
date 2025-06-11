#!/usr/bin/env python3
"""
远程API测试脚本
测试通过SSH端口转发访问的远程Surya API服务
"""

import requests
import json
import time
import os
from pathlib import Path

# API配置
API_BASE_URL = "http://localhost:8090"
TEST_PDF_PATH = "test_files/sample.pdf"  # 测试PDF文件路径

def test_api_health():
    """测试API健康状态"""
    print("🔍 测试API健康状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API服务正常运行")
            print(f"   状态: {data.get('status', 'unknown')}")
            print(f"   时间: {data.get('timestamp', 'unknown')}")
            return True
        else:
            print(f"❌ API健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务")
        print("请检查:")
        print("  1. 远程服务是否启动: ./scripts/remote_dev.sh status")
        print("  2. 端口转发是否建立: ./scripts/local_tunnel.sh")
        return False
    except Exception as e:
        print(f"❌ API健康检查异常: {e}")
        return False

def test_convert_pdf():
    """测试PDF转换功能"""
    print("\n📄 测试PDF转换功能...")
    
    # 检查测试文件
    if not os.path.exists(TEST_PDF_PATH):
        print(f"⚠️  测试文件不存在: {TEST_PDF_PATH}")
        print("请提供一个测试PDF文件，或修改TEST_PDF_PATH变量")
        return False
    
    try:
        # 准备文件上传
        with open(TEST_PDF_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_PDF_PATH), f, 'application/pdf')}
            data = {
                'max_pages': 2,  # 只转换前2页进行测试
                'task_type': 'ocr_without_boxes'
            }
            
            print(f"📤 上传文件: {TEST_PDF_PATH}")
            print(f"   最大页数: {data['max_pages']}")
            print(f"   任务类型: {data['task_type']}")
            
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/convert",
                files=files,
                data=data,
                timeout=300  # 5分钟超时
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                print("✅ PDF转换成功")
                print(f"   处理时间: {end_time - start_time:.2f}秒")
                print(f"   页面数量: {result.get('page_count', 'unknown')}")
                print(f"   输出长度: {len(result.get('markdown', ''))}")
                
                # 保存结果
                output_file = f"test_output_{int(time.time())}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.get('markdown', ''))
                print(f"   结果已保存: {output_file}")
                
                return True
            else:
                print(f"❌ PDF转换失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ 请求超时，可能是文件太大或服务器处理时间过长")
        return False
    except Exception as e:
        print(f"❌ PDF转换异常: {e}")
        return False

def test_api_info():
    """测试API信息接口"""
    print("\n📊 获取API信息...")
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API信息获取成功")
            print(f"   服务名称: {data.get('name', 'unknown')}")
            print(f"   版本: {data.get('version', 'unknown')}")
            print(f"   描述: {data.get('description', 'unknown')}")
            return True
        else:
            print(f"❌ API信息获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API信息获取异常: {e}")
        return False

def create_test_pdf():
    """创建一个简单的测试PDF文件"""
    print("\n📝 创建测试PDF文件...")
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # 创建测试目录
        os.makedirs("test_files", exist_ok=True)
        
        # 创建简单的PDF
        c = canvas.Canvas(TEST_PDF_PATH, pagesize=letter)
        c.drawString(100, 750, "这是一个测试PDF文件")
        c.drawString(100, 730, "用于测试Surya OCR API服务")
        c.drawString(100, 710, "Test PDF for Surya OCR API")
        c.drawString(100, 690, "Page 1 content")
        
        # 添加第二页
        c.showPage()
        c.drawString(100, 750, "第二页内容")
        c.drawString(100, 730, "Page 2 content")
        
        c.save()
        print(f"✅ 测试PDF创建成功: {TEST_PDF_PATH}")
        return True
        
    except ImportError:
        print("⚠️  reportlab未安装，无法创建测试PDF")
        print("请安装: pip install reportlab")
        print("或者手动提供一个测试PDF文件")
        return False
    except Exception as e:
        print(f"❌ 创建测试PDF失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 远程Surya API测试")
    print(f"   API地址: {API_BASE_URL}")
    print(f"   测试文件: {TEST_PDF_PATH}")
    print("=" * 50)
    
    # 测试API健康状态
    if not test_api_health():
        print("\n❌ API服务不可用，测试终止")
        return
    
    # 测试API信息
    test_api_info()
    
    # 检查测试文件，如果不存在则尝试创建
    if not os.path.exists(TEST_PDF_PATH):
        if not create_test_pdf():
            print("\n⚠️  无测试文件，跳过PDF转换测试")
            return
    
    # 测试PDF转换
    test_convert_pdf()
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    main() 