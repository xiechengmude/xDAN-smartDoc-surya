#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF 到 Markdown API 测试脚本
此脚本用于测试 PDF 到 Markdown 转换 API
"""

import argparse
import os
import sys
import time
import requests
import json


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='测试 PDF 到 Markdown 转换 API')
    parser.add_argument('--pdf', type=str, required=True, help='PDF 文件路径')
    parser.add_argument('--url', type=str, default='http://localhost:8000', help='API 服务地址')
    parser.add_argument('--api-key', type=str, required=True, help='API 密钥')
    parser.add_argument('--output', type=str, help='输出 Markdown 文件路径')
    parser.add_argument('--timeout', type=int, default=300, help='等待转换完成的超时时间（秒）')
    parser.add_argument('--interval', type=int, default=5, help='检查转换状态的间隔时间（秒）')
    
    return parser.parse_args()


def upload_pdf(api_url, pdf_path, api_key):
    """上传 PDF 文件到 API 服务"""
    print(f"正在上传 PDF 文件: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"错误: PDF 文件不存在: {pdf_path}")
        sys.exit(1)
    
    try:
        with open(pdf_path, 'rb') as pdf_file:
            files = {'file': (os.path.basename(pdf_path), pdf_file, 'application/pdf')}
            headers = {'X-API-Key': api_key}
            response = requests.post(f"{api_url}/convert", files=files, headers=headers)
            
            if response.status_code != 200:
                print(f"错误: API 请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                sys.exit(1)
            
            result = response.json()
            task_id = result.get('task_id')
            print(f"PDF 上传成功，任务 ID: {task_id}")
            return task_id
    except Exception as e:
        print(f"错误: 上传 PDF 文件时发生异常: {str(e)}")
        sys.exit(1)


def check_conversion_status(api_url, task_id, api_key, timeout=300, interval=5):
    """检查转换任务状态"""
    print(f"正在等待转换完成，任务 ID: {task_id}")
    
    elapsed_time = 0
    while elapsed_time < timeout:
        try:
            headers = {'X-API-Key': api_key}
            response = requests.get(f"{api_url}/status/{task_id}", headers=headers)
            
            if response.status_code != 200:
                print(f"错误: 获取任务状态失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                sys.exit(1)
            
            result = response.json()
            status = result.get('status')
            
            if status == 'completed':
                print("转换完成!")
                return result.get('markdown')
            elif status == 'failed':
                print(f"错误: 转换失败: {result.get('error')}")
                sys.exit(1)
            elif status == 'processing':
                print(f"转换中... (已等待 {elapsed_time} 秒)")
            else:
                print(f"未知状态: {status}")
            
            time.sleep(interval)
            elapsed_time += interval
        except Exception as e:
            print(f"错误: 检查任务状态时发生异常: {str(e)}")
            sys.exit(1)
    
    print(f"错误: 转换超时，已等待 {timeout} 秒")
    sys.exit(1)


def save_markdown(markdown_text, output_path):
    """保存 Markdown 文本到文件"""
    if not output_path:
        print("未指定输出文件路径，将直接打印 Markdown 内容")
        print("\n" + "=" * 50 + " MARKDOWN 内容 " + "=" * 50)
        print(markdown_text)
        print("=" * 120)
        return
    
    try:
        with open(output_path, 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_text)
        print(f"Markdown 内容已保存到: {output_path}")
    except Exception as e:
        print(f"错误: 保存 Markdown 文件时发生异常: {str(e)}")
        sys.exit(1)


def main():
    """主函数"""
    args = parse_arguments()
    
    # 上传 PDF 文件
    task_id = upload_pdf(args.url, args.pdf, args.api_key)
    
    # 检查转换状态
    markdown_text = check_conversion_status(args.url, task_id, args.api_key, args.timeout, args.interval)
    
    # 保存 Markdown 内容
    save_markdown(markdown_text, args.output)
    
    print("测试完成!")


if __name__ == "__main__":
    main()
