#!/usr/bin/env python3
"""
xDAN Smart API 增强版客户端
包含完善的超时处理和重试机制
"""

import requests
import time
import os
from typing import Optional, Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """超时异常"""
    pass

class XDANSmartClientEnhanced:
    """xDAN Smart API 增强版客户端，包含完善的超时处理"""
    
    def __init__(self, 
                 base_url: str = "http://159.54.182.15:8000", 
                 api_key: str = "QQ-6Bb3uVTIH9I4Q2SNYnh6Ias-u3oMSqi-UW5YORxM",
                 request_timeout: int = 30,
                 upload_timeout: int = 120,
                 status_timeout: int = 10,
                 max_wait_time: int = 1800,  # 30分钟
                 retry_attempts: int = 3):
        """
        初始化客户端
        
        Args:
            base_url: API服务器地址
            api_key: API密钥
            request_timeout: 请求超时时间（秒）
            upload_timeout: 文件上传超时时间（秒）
            status_timeout: 状态查询超时时间（秒）
            max_wait_time: 最大等待时间（秒）
            retry_attempts: 重试次数
        """
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
        self.request_timeout = request_timeout
        self.upload_timeout = upload_timeout
        self.status_timeout = status_timeout
        self.max_wait_time = max_wait_time
        self.retry_attempts = retry_attempts
        
        logger.info(f"初始化客户端: {base_url}")
        logger.info(f"超时配置: 请求={request_timeout}s, 上传={upload_timeout}s, 状态查询={status_timeout}s, 最大等待={max_wait_time}s")
    
    def convert_from_url(self, pdf_url: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        通过URL转换PDF为Markdown（带超时处理）
        
        Args:
            pdf_url: PDF文件的URL
            output_file: 输出文件路径（可选）
            
        Returns:
            转换后的Markdown内容，失败返回None
        """
        logger.info(f"开始转换PDF: {pdf_url}")
        
        # 1. 提交转换任务（带重试）
        task_id = self._submit_url_task_with_retry(pdf_url)
        if not task_id:
            return None
        
        # 2. 等待处理完成（带超时）
        try:
            return self._wait_for_completion_with_timeout(task_id, output_file)
        except TimeoutError as e:
            logger.error(f"转换超时: {e}")
            return None
    
    def convert_from_file(self, file_path: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        上传本地PDF文件进行转换（带超时处理）
        
        Args:
            file_path: 本地PDF文件路径
            output_file: 输出文件路径（可选）
            
        Returns:
            转换后的Markdown内容，失败返回None
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
        
        logger.info(f"上传文件: {file_path}")
        
        # 1. 上传文件（带重试）
        task_id = self._upload_file_with_retry(file_path)
        if not task_id:
            return None
        
        # 2. 等待处理完成（带超时）
        try:
            return self._wait_for_completion_with_timeout(task_id, output_file)
        except TimeoutError as e:
            logger.error(f"转换超时: {e}")
            return None
    
    def _submit_url_task_with_retry(self, pdf_url: str) -> Optional[str]:
        """提交URL任务（带重试机制）"""
        payload = {"url": pdf_url}
        headers = {**self.headers, "Content-Type": "application/json"}
        
        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.info(f"提交任务 (尝试 {attempt}/{self.retry_attempts})")
                response = requests.post(
                    f"{self.base_url}/convert-url", 
                    headers=headers, 
                    json=payload, 
                    timeout=self.request_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("task_id")
                    logger.info(f"任务提交成功: {task_id}")
                    return task_id
                else:
                    logger.warning(f"任务提交失败: HTTP {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt}/{self.retry_attempts})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求异常 (尝试 {attempt}/{self.retry_attempts}): {e}")
            except Exception as e:
                logger.error(f"未知异常 (尝试 {attempt}/{self.retry_attempts}): {e}")
            
            if attempt < self.retry_attempts:
                wait_time = 2 ** attempt  # 指数退避
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        logger.error("所有重试尝试都失败了")
        return None
    
    def _upload_file_with_retry(self, file_path: str) -> Optional[str]:
        """上传文件（带重试机制）"""
        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.info(f"上传文件 (尝试 {attempt}/{self.retry_attempts})")
                with open(file_path, "rb") as f:
                    files = {"file": f}
                    response = requests.post(
                        f"{self.base_url}/convert", 
                        headers=self.headers, 
                        files=files, 
                        timeout=self.upload_timeout
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("task_id")
                    logger.info(f"文件上传成功: {task_id}")
                    return task_id
                else:
                    logger.warning(f"文件上传失败: HTTP {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"上传超时 (尝试 {attempt}/{self.retry_attempts})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"上传异常 (尝试 {attempt}/{self.retry_attempts}): {e}")
            except Exception as e:
                logger.error(f"未知异常 (尝试 {attempt}/{self.retry_attempts}): {e}")
            
            if attempt < self.retry_attempts:
                wait_time = 2 ** attempt
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        logger.error("所有重试尝试都失败了")
        return None
    
    def _wait_for_completion_with_timeout(self, task_id: str, output_file: Optional[str] = None) -> Optional[str]:
        """等待任务完成（带超时处理）"""
        logger.info(f"等待任务完成: {task_id}")
        start_time = time.time()
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        while True:
            elapsed = time.time() - start_time
            
            # 检查总超时
            if elapsed > self.max_wait_time:
                raise TimeoutError(f"任务处理超时，已等待 {elapsed:.1f} 秒（最大等待时间: {self.max_wait_time} 秒）")
            
            try:
                response = requests.get(
                    f"{self.base_url}/status/{task_id}", 
                    headers=self.headers, 
                    timeout=self.status_timeout
                )
                
                if response.status_code == 200:
                    consecutive_failures = 0  # 重置失败计数
                    result = response.json()
                    status = result.get("status")
                    
                    if status == "processing":
                        logger.info(f"处理中... (已等待: {elapsed:.1f}s)")
                    elif status == "completed":
                        markdown = result.get("markdown", "")
                        logger.info(f"转换完成! (总耗时: {elapsed:.1f}s)")
                        
                        # 分析和保存结果
                        self._analyze_result(markdown)
                        if output_file:
                            self._save_to_file(markdown, output_file)
                        
                        return markdown
                        
                    elif status == "failed":
                        error = result.get("error", "未知错误")
                        logger.error(f"转换失败: {error}")
                        return None
                    
                else:
                    consecutive_failures += 1
                    logger.warning(f"状态查询失败: HTTP {response.status_code} (连续失败: {consecutive_failures})")
                    
            except requests.exceptions.Timeout:
                consecutive_failures += 1
                logger.warning(f"状态查询超时 (连续失败: {consecutive_failures})")
            except requests.exceptions.RequestException as e:
                consecutive_failures += 1
                logger.warning(f"状态查询异常: {e} (连续失败: {consecutive_failures})")
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"未知异常: {e} (连续失败: {consecutive_failures})")
            
            # 检查连续失败次数
            if consecutive_failures >= max_consecutive_failures:
                raise TimeoutError(f"连续 {consecutive_failures} 次状态查询失败，可能服务器不可用")
            
            # 动态调整等待时间
            if consecutive_failures > 0:
                wait_time = min(10, 3 + consecutive_failures)  # 失败时等待更长时间
            else:
                wait_time = 3  # 正常等待时间
            
            time.sleep(wait_time)
    
    def _analyze_result(self, markdown: str):
        """分析转换结果"""
        if not markdown:
            return
        
        lines = markdown.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        page_markers = [line for line in lines if "第" in line and "页" in line]
        
        logger.info("转换结果分析:")
        logger.info(f"  总字符数: {len(markdown):,}")
        logger.info(f"  有效行数: {len(non_empty_lines):,}")
        logger.info(f"  检测页数: {len(page_markers)}")
        
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
            logger.info(f"文件已保存: {file_path}")
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态（单次查询）"""
        try:
            response = requests.get(
                f"{self.base_url}/status/{task_id}", 
                headers=self.headers, 
                timeout=self.status_timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"状态查询失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"状态查询异常: {e}")
            return None

def main():
    """主函数 - 增强版客户端示例"""
    print("🚀 xDAN Smart API 增强版客户端示例")
    print("=" * 60)
    
    # 创建增强版客户端
    client = XDANSmartClientEnhanced(
        request_timeout=30,      # 请求超时30秒
        upload_timeout=120,      # 上传超时2分钟
        status_timeout=10,       # 状态查询超时10秒
        max_wait_time=1800,      # 最大等待30分钟
        retry_attempts=3         # 重试3次
    )
    
    # 示例: 通过URL转换PDF
    print("\n📋 示例: 通过URL转换PDF（带完善超时处理）")
    pdf_url = "https://www.cbd.int/doc/c/d851/4e37/449bb1fdb754412f1ab5d9c5/cop-14-l-06-zh.pdf"
    
    try:
        markdown_content = client.convert_from_url(pdf_url, "enhanced_output.md")
        
        if markdown_content:
            print("✅ 转换成功!")
            print(f"📊 内容长度: {len(markdown_content):,} 字符")
        else:
            print("❌ 转换失败!")
            
    except TimeoutError as e:
        print(f"⏰ 转换超时: {e}")
    except Exception as e:
        print(f"❌ 转换异常: {e}")
    
    print("\n🎉 增强版客户端示例完成!")

if __name__ == "__main__":
    main() 