#!/usr/bin/env python3
"""
并发性能测试脚本 - 使用较小的PDF文件测试并发处理能力
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置信息
API_BASE_URL = "http://159.54.182.15:8000"
API_KEY = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM"

# 测试PDF文件列表 - 选择较小的文件
TEST_PDFS = [
    {
        "name": "生物多样性公约文件",
        "url": "https://www.cbd.int/doc/c/d851/4e37/449bb1fdb754412f1ab5d9c5/cop-14-l-06-zh.pdf"
    },
    {
        "name": "生态环境部文件1",
        "url": "https://www.mee.gov.cn/gkml/hbb/bgt/201707/W020170728397753220005.pdf"
    },
    {
        "name": "生态环境部文件2",
        "url": "https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/stzl/202011/W020201127553309828533.pdf"
    }
]

class TestResult:
    def __init__(self):
        self.results = []
        self.lock = threading.Lock()
    
    def add_result(self, result):
        with self.lock:
            self.results.append(result)

def submit_and_wait(pdf_info, result_collector):
    """提交任务并等待完成"""
    pdf_name = pdf_info["name"]
    pdf_url = pdf_info["url"]
    
    start_time = time.time()
    
    try:
        # 1. 提交任务
        print(f"📤 [{pdf_name}] 提交任务...")
        payload = {"url": pdf_url}
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        response = requests.post(f"{API_BASE_URL}/convert-url", headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            result = {
                "name": pdf_name,
                "status": "submit_failed",
                "error": f"HTTP {response.status_code}",
                "total_time": time.time() - start_time
            }
            result_collector.add_result(result)
            print(f"❌ [{pdf_name}] 提交失败: {response.status_code}")
            return result
        
        task_data = response.json()
        task_id = task_data.get("task_id")
        submit_time = time.time() - start_time
        print(f"✅ [{pdf_name}] 任务提交成功: {task_id} (耗时: {submit_time:.2f}s)")
        
        # 2. 等待完成
        wait_start = time.time()
        last_status = None
        
        while True:
            try:
                response = requests.get(f"{API_BASE_URL}/status/{task_id}", headers={"X-API-Key": API_KEY}, timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get("status")
                    
                    if status != last_status:
                        if status == "processing":
                            elapsed = time.time() - wait_start
                            print(f"🔄 [{pdf_name}] 处理中... (已等待: {elapsed:.1f}s)")
                        elif status == "completed":
                            total_time = time.time() - start_time
                            markdown = status_data.get("markdown", "")
                            
                            # 分析结果
                            lines = markdown.split('\n') if markdown else []
                            page_markers = [line for line in lines if "第" in line and "页" in line]
                            pages = len(page_markers) if page_markers else 0
                            
                            result = {
                                "name": pdf_name,
                                "status": "completed",
                                "total_time": total_time,
                                "submit_time": submit_time,
                                "wait_time": time.time() - wait_start,
                                "pages": pages,
                                "markdown_length": len(markdown),
                                "task_id": task_id
                            }
                            result_collector.add_result(result)
                            
                            print(f"✅ [{pdf_name}] 完成! 总时间: {total_time:.2f}s, 页数: {pages}, 长度: {len(markdown):,}")
                            return result
                            
                        elif status == "failed":
                            error = status_data.get("error", "未知错误")
                            result = {
                                "name": pdf_name,
                                "status": "failed",
                                "error": error,
                                "total_time": time.time() - start_time,
                                "task_id": task_id
                            }
                            result_collector.add_result(result)
                            print(f"❌ [{pdf_name}] 失败: {error}")
                            return result
                        
                        last_status = status
                
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ [{pdf_name}] 状态查询异常: {e}")
                time.sleep(3)
        
    except Exception as e:
        result = {
            "name": pdf_name,
            "status": "exception",
            "error": str(e),
            "total_time": time.time() - start_time
        }
        result_collector.add_result(result)
        print(f"❌ [{pdf_name}] 异常: {e}")
        return result

def test_sequential():
    """顺序处理测试"""
    print("\n" + "="*60)
    print("📊 顺序处理测试")
    print("="*60)
    
    results = TestResult()
    start_time = time.time()
    
    for i, pdf_info in enumerate(TEST_PDFS, 1):
        print(f"\n🔄 处理第 {i}/{len(TEST_PDFS)} 个文件...")
        submit_and_wait(pdf_info, results)
    
    total_time = time.time() - start_time
    print(f"\n📊 顺序处理完成，总耗时: {total_time:.2f}s")
    
    return results, total_time

def test_concurrent():
    """并发处理测试"""
    print("\n" + "="*60)
    print("🚀 并发处理测试")
    print("="*60)
    
    results = TestResult()
    start_time = time.time()
    
    # 并发提交和等待
    with ThreadPoolExecutor(max_workers=len(TEST_PDFS)) as executor:
        futures = {
            executor.submit(submit_and_wait, pdf_info, results): pdf_info["name"]
            for pdf_info in TEST_PDFS
        }
        
        print(f"📤 已提交 {len(futures)} 个并发任务...")
        
        for future in as_completed(futures):
            pdf_name = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"❌ [{pdf_name}] 并发处理异常: {e}")
    
    total_time = time.time() - start_time
    print(f"\n📊 并发处理完成，总耗时: {total_time:.2f}s")
    
    return results, total_time

def print_summary(seq_results, seq_time, conc_results, conc_time):
    """打印测试总结"""
    print("\n" + "="*80)
    print("📈 性能测试总结")
    print("="*80)
    
    print(f"\n📊 基本统计:")
    print(f"   测试文件数量: {len(TEST_PDFS)}")
    
    # 顺序处理统计
    seq_completed = len([r for r in seq_results.results if r["status"] == "completed"])
    seq_failed = len([r for r in seq_results.results if r["status"] != "completed"])
    seq_total_pages = sum(r.get("pages", 0) for r in seq_results.results if r["status"] == "completed")
    
    print(f"\n🔄 顺序处理:")
    print(f"   总耗时: {seq_time:.2f}s")
    print(f"   成功: {seq_completed}/{len(TEST_PDFS)}")
    print(f"   失败: {seq_failed}")
    print(f"   总页数: {seq_total_pages}")
    if seq_total_pages > 0:
        print(f"   平均每页时间: {seq_time/seq_total_pages:.2f}s")
    
    # 并发处理统计
    conc_completed = len([r for r in conc_results.results if r["status"] == "completed"])
    conc_failed = len([r for r in conc_results.results if r["status"] != "completed"])
    conc_total_pages = sum(r.get("pages", 0) for r in conc_results.results if r["status"] == "completed")
    
    print(f"\n🚀 并发处理:")
    print(f"   总耗时: {conc_time:.2f}s")
    print(f"   成功: {conc_completed}/{len(TEST_PDFS)}")
    print(f"   失败: {conc_failed}")
    print(f"   总页数: {conc_total_pages}")
    if conc_total_pages > 0:
        print(f"   平均每页时间: {conc_time/conc_total_pages:.2f}s")
    
    # 性能对比
    if seq_time > 0 and conc_time > 0:
        speedup = seq_time / conc_time
        print(f"\n⚡ 性能提升:")
        print(f"   并发加速比: {speedup:.2f}x")
        print(f"   时间节省: {seq_time - conc_time:.2f}s ({((seq_time - conc_time)/seq_time*100):.1f}%)")
    
    # 详细结果
    print(f"\n📋 详细结果:")
    print(f"{'文件名':<25} {'状态':<10} {'总时间':<8} {'页数':<6} {'长度':<8}")
    print("-" * 65)
    
    for result in conc_results.results:
        name = result["name"][:23] + ".." if len(result["name"]) > 25 else result["name"]
        status = result["status"]
        total_time = f"{result.get('total_time', 0):.1f}s"
        pages = str(result.get("pages", 0))
        length = f"{result.get('markdown_length', 0):,}"
        
        print(f"{name:<25} {status:<10} {total_time:<8} {pages:<6} {length:<8}")

def main():
    print("🚀 远程API并发性能测试")
    print(f"🌐 服务器: {API_BASE_URL}")
    print(f"📄 测试文件数量: {len(TEST_PDFS)}")
    
    print("\n📋 测试文件列表:")
    for i, pdf in enumerate(TEST_PDFS, 1):
        print(f"   {i}. {pdf['name']}")
    
    # 1. 顺序处理测试
    seq_results, seq_time = test_sequential()
    
    # 等待服务器稳定
    print("\n⏸️  等待5秒让服务器稳定...")
    time.sleep(5)
    
    # 2. 并发处理测试
    conc_results, conc_time = test_concurrent()
    
    # 3. 打印总结
    print_summary(seq_results, seq_time, conc_results, conc_time)
    
    print("\n🎉 测试完成!")

if __name__ == "__main__":
    main() 