#!/usr/bin/env python3
"""
远程 xDAN Smart API 高性能测试脚本
测试批量处理优化的性能提升效果
"""

import requests
import time
import json
import asyncio
import aiohttp
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import threading

# 配置信息
API_BASE_URL = "http://159.54.182.15:8000"
API_KEY = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"

# 测试PDF文件列表
TEST_PDFS = [
    {
        "name": "澳门科技大学年度学术报告",
        "url": "https://www.must.edu.mo/images/RATO/publication/2008-annual-academic-report.pdf",
        "expected_pages": "约50-100页"
    },
    {
        "name": "生物多样性公约COP-14文件",
        "url": "https://www.cbd.int/doc/c/d851/4e37/449bb1fdb754412f1ab5d9c5/cop-14-l-06-zh.pdf",
        "expected_pages": "约20-50页"
    },
    {
        "name": "IFC环境社会可持续性指导说明",
        "url": "https://www.ifc.org/content/dam/ifc/doc/2010/20190627-ifc-ps-guidance-note-6-cn.pdf",
        "expected_pages": "约30-80页"
    },
    {
        "name": "生态环境部标准文件1",
        "url": "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/stzl/202011/W020201127553309828533.pdf",
        "expected_pages": "约20-60页"
    },
    {
        "name": "生态环境部标准文件2", 
        "url": "https://www.mee.gov.cn/gkml/hbb/bgt/201707/W020170728397753220005.pdf",
        "expected_pages": "约10-40页"
    }
]

# 请求头
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

class PerformanceTestResult:
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        self.total_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.total_pages = 0
        self.total_processing_time = 0.0
        self.lock = threading.Lock()

    def add_result(self, result: Dict[str, Any]):
        with self.lock:
            self.results.append(result)
            if result['status'] == 'completed':
                self.successful_files += 1
                self.total_pages += result.get('pages_processed', 0)
                self.total_processing_time += result.get('processing_time', 0)
            else:
                self.failed_files += 1

def test_api_connection():
    """测试API连接和性能统计"""
    print("🔗 测试API连接和当前性能状态...")
    try:
        response = requests.get(f"{API_BASE_URL}/performance", headers={"X-API-Key": API_KEY}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API连接成功")
            print(f"   设备类型: {data.get('device_type')}")
            print(f"   最大并发任务数: {data.get('max_concurrent_tasks')}")
            print(f"   当前并发任务数: {data.get('current_concurrent_tasks')}")
            print(f"   已处理文档总数: {data.get('total_processed')}")
            print(f"   已处理页面总数: {data.get('total_pages')}")
            print(f"   平均每页处理时间: {data.get('average_time_per_page', 0):.3f}s")
            print(f"   批处理大小: {data.get('batch_sizes')}")
            return True
        else:
            print(f"❌ API连接失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API连接异常: {e}")
        return False

def submit_conversion_task(pdf_info: Dict[str, str]) -> str:
    """提交PDF转换任务"""
    try:
        payload = {"url": pdf_info["url"]}
        response = requests.post(f"{API_BASE_URL}/convert-url", headers=HEADERS, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print(f"✅ 任务提交成功: {pdf_info['name']} -> {task_id}")
            return task_id
        else:
            print(f"❌ 任务提交失败: {pdf_info['name']} - {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 任务提交异常: {pdf_info['name']} - {e}")
        return None

def wait_for_task_completion(task_id: str, pdf_name: str, max_wait_time: int = 600) -> Dict[str, Any]:
    """等待任务完成并返回结果"""
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(f"{API_BASE_URL}/status/{task_id}", headers={"X-API-Key": API_KEY}, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status")
                
                # 只在状态变化时打印
                if status != last_status:
                    if status == "processing":
                        pages_processed = result.get("pages_processed", 0)
                        print(f"🔄 {pdf_name}: 处理中... (已处理页面: {pages_processed})")
                    elif status == "completed":
                        processing_time = result.get("processing_time", 0)
                        total_pages = result.get("pages_processed", 0)
                        print(f"✅ {pdf_name}: 完成! 处理时间: {processing_time:.2f}s, 页面数: {total_pages}")
                        return {
                            'task_id': task_id,
                            'pdf_name': pdf_name,
                            'status': 'completed',
                            'processing_time': processing_time,
                            'pages_processed': total_pages,
                            'markdown_length': len(result.get('markdown', '')),
                            'wait_time': time.time() - start_time
                        }
                    elif status == "failed":
                        error = result.get("error", "未知错误")
                        print(f"❌ {pdf_name}: 失败 - {error}")
                        return {
                            'task_id': task_id,
                            'pdf_name': pdf_name,
                            'status': 'failed',
                            'error': error,
                            'wait_time': time.time() - start_time
                        }
                    
                    last_status = status
            
            time.sleep(2)  # 每2秒检查一次
            
        except Exception as e:
            print(f"❌ {pdf_name}: 状态查询异常 - {e}")
            time.sleep(5)
    
    print(f"⏰ {pdf_name}: 等待超时 ({max_wait_time}s)")
    return {
        'task_id': task_id,
        'pdf_name': pdf_name,
        'status': 'timeout',
        'wait_time': max_wait_time
    }

def test_sequential_processing():
    """测试顺序处理性能"""
    print("\n" + "="*60)
    print("📊 顺序处理性能测试")
    print("="*60)
    
    results = PerformanceTestResult()
    results.start_time = time.time()
    results.total_files = len(TEST_PDFS)
    
    for i, pdf_info in enumerate(TEST_PDFS, 1):
        print(f"\n🔄 处理第 {i}/{len(TEST_PDFS)} 个文件: {pdf_info['name']}")
        
        # 提交任务
        task_id = submit_conversion_task(pdf_info)
        if task_id:
            # 等待完成
            result = wait_for_task_completion(task_id, pdf_info['name'])
            results.add_result(result)
        else:
            results.add_result({
                'task_id': None,
                'pdf_name': pdf_info['name'],
                'status': 'submit_failed'
            })
    
    results.end_time = time.time()
    return results

def test_concurrent_processing():
    """测试并发处理性能"""
    print("\n" + "="*60)
    print("🚀 并发处理性能测试")
    print("="*60)
    
    results = PerformanceTestResult()
    results.start_time = time.time()
    results.total_files = len(TEST_PDFS)
    
    # 提交所有任务
    tasks = []
    print("📤 批量提交所有转换任务...")
    for pdf_info in TEST_PDFS:
        task_id = submit_conversion_task(pdf_info)
        if task_id:
            tasks.append((task_id, pdf_info['name']))
    
    print(f"✅ 成功提交 {len(tasks)} 个任务，开始并发等待...")
    
    # 并发等待所有任务完成
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_task = {
            executor.submit(wait_for_task_completion, task_id, pdf_name): (task_id, pdf_name)
            for task_id, pdf_name in tasks
        }
        
        for future in as_completed(future_to_task):
            task_id, pdf_name = future_to_task[future]
            try:
                result = future.result()
                results.add_result(result)
            except Exception as e:
                print(f"❌ {pdf_name}: 处理异常 - {e}")
                results.add_result({
                    'task_id': task_id,
                    'pdf_name': pdf_name,
                    'status': 'exception',
                    'error': str(e)
                })
    
    results.end_time = time.time()
    return results

def print_performance_summary(sequential_results: PerformanceTestResult, concurrent_results: PerformanceTestResult):
    """打印性能测试总结"""
    print("\n" + "="*80)
    print("📈 性能测试总结报告")
    print("="*80)
    
    # 基本统计
    print(f"\n📊 基本统计:")
    print(f"   测试文件数量: {len(TEST_PDFS)}")
    
    # 顺序处理结果
    seq_total_time = sequential_results.end_time - sequential_results.start_time
    print(f"\n🔄 顺序处理结果:")
    print(f"   总耗时: {seq_total_time:.2f}s")
    print(f"   成功文件: {sequential_results.successful_files}/{sequential_results.total_files}")
    print(f"   失败文件: {sequential_results.failed_files}")
    print(f"   总页面数: {sequential_results.total_pages}")
    print(f"   总处理时间: {sequential_results.total_processing_time:.2f}s")
    if sequential_results.total_pages > 0:
        print(f"   平均每页处理时间: {sequential_results.total_processing_time/sequential_results.total_pages:.3f}s")
    
    # 并发处理结果
    conc_total_time = concurrent_results.end_time - concurrent_results.start_time
    print(f"\n🚀 并发处理结果:")
    print(f"   总耗时: {conc_total_time:.2f}s")
    print(f"   成功文件: {concurrent_results.successful_files}/{concurrent_results.total_files}")
    print(f"   失败文件: {concurrent_results.failed_files}")
    print(f"   总页面数: {concurrent_results.total_pages}")
    print(f"   总处理时间: {concurrent_results.total_processing_time:.2f}s")
    if concurrent_results.total_pages > 0:
        print(f"   平均每页处理时间: {concurrent_results.total_processing_time/concurrent_results.total_pages:.3f}s")
    
    # 性能对比
    if seq_total_time > 0 and conc_total_time > 0:
        speedup = seq_total_time / conc_total_time
        print(f"\n⚡ 性能提升:")
        print(f"   并发处理速度提升: {speedup:.2f}x")
        print(f"   时间节省: {seq_total_time - conc_total_time:.2f}s ({((seq_total_time - conc_total_time)/seq_total_time*100):.1f}%)")
    
    # 详细结果
    print(f"\n📋 详细处理结果:")
    print(f"{'文件名':<30} {'状态':<10} {'处理时间':<10} {'页面数':<8} {'Markdown长度':<12}")
    print("-" * 80)
    
    for result in concurrent_results.results:
        name = result['pdf_name'][:28] + ".." if len(result['pdf_name']) > 30 else result['pdf_name']
        status = result['status']
        proc_time = f"{result.get('processing_time', 0):.2f}s" if result.get('processing_time') else "N/A"
        pages = str(result.get('pages_processed', 0)) if result.get('pages_processed') else "N/A"
        md_len = str(result.get('markdown_length', 0)) if result.get('markdown_length') else "N/A"
        
        print(f"{name:<30} {status:<10} {proc_time:<10} {pages:<8} {md_len:<12}")

def test_api_performance_endpoint():
    """测试API性能统计端点"""
    print("\n📊 获取最终性能统计...")
    try:
        response = requests.get(f"{API_BASE_URL}/performance", headers={"X-API-Key": API_KEY}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ 最终性能统计:")
            print(f"   已处理文档总数: {data.get('total_processed')}")
            print(f"   已处理页面总数: {data.get('total_pages')}")
            print(f"   总处理时间: {data.get('total_processing_time', 0):.2f}s")
            print(f"   平均每页处理时间: {data.get('average_time_per_page', 0):.3f}s")
            print(f"   当前并发任务数: {data.get('current_concurrent_tasks')}")
            return data
        else:
            print(f"❌ 性能统计获取失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 性能统计异常: {e}")
        return None

def main():
    """主测试函数"""
    print("🚀 xDAN Smart API 高性能测试开始")
    print(f"🌐 服务器地址: {API_BASE_URL}")
    print(f"🔑 API密钥: {API_KEY}")
    print(f"📄 测试文件数量: {len(TEST_PDFS)}")
    print("="*80)
    
    # 显示测试文件列表
    print("📋 测试文件列表:")
    for i, pdf in enumerate(TEST_PDFS, 1):
        print(f"   {i}. {pdf['name']} ({pdf['expected_pages']})")
        print(f"      URL: {pdf['url']}")
    
    # 1. 测试API连接
    if not test_api_connection():
        print("❌ API连接失败，终止测试")
        return
    
    # 2. 顺序处理测试
    print("\n⏳ 开始顺序处理测试...")
    sequential_results = test_sequential_processing()
    
    # 等待一段时间让服务器稳定
    print("\n⏸️  等待10秒让服务器稳定...")
    time.sleep(10)
    
    # 3. 并发处理测试
    print("\n⏳ 开始并发处理测试...")
    concurrent_results = test_concurrent_processing()
    
    # 4. 打印性能总结
    print_performance_summary(sequential_results, concurrent_results)
    
    # 5. 获取最终性能统计
    test_api_performance_endpoint()
    
    print("\n🎉 高性能测试完成！")

if __name__ == "__main__":
    main() 