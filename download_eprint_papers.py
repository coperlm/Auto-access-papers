#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量下载IACR eprint论文

从paper_eprint_urls.json读取论文信息和eprint链接，
然后下载论文并以"[作者]-[标题].pdf"的格式保存。
"""

# 确保使用UTF-8编码，避免中文显示乱码
import sys
import locale
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import os
import time
import re
import requests
from urllib.parse import urlparse, urljoin
from tqdm import tqdm

# 配置
DOWNLOAD_FOLDER = "papers"  # 论文保存的文件夹
INPUT_FILE = "paper_eprint_urls.json"  # 包含eprint链接的输入文件
MAX_RETRIES = 3  # 下载失败时的最大重试次数
DELAY_BETWEEN_DOWNLOADS = 2  # 两次下载之间的延迟（秒）
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def sanitize_filename(filename):
    """
    将字符串转换为合法的文件名
    """
    # 移除或替换不允许用于文件名的字符
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # 替换多个空格为单个空格
    filename = re.sub(r'\s+', ' ', filename).strip()
    # 限制文件名长度
    if len(filename) > 150:
        filename = filename[:147] + "..."
    return filename


def extract_pdf_url_from_eprint_url(eprint_url):
    """
    从eprint URL中提取PDF下载链接
    
    IACR eprint通常格式为 https://eprint.iacr.org/YYYY/NNNN
    对应的PDF链接通常为 https://eprint.iacr.org/YYYY/NNNN.pdf
    """
    # 清理URL，移除可能的查询参数或片段标识符
    base_url = eprint_url.split('#')[0].split('?')[0].rstrip('/')
    # 添加.pdf扩展名
    return f"{base_url}.pdf"


def download_file(url, output_path, max_retries=3):
    """
    下载文件并显示进度条
    
    Args:
        url: 要下载的文件URL
        output_path: 保存文件的路径
        max_retries: 最大重试次数
    
    Returns:
        bool: 下载成功返回True，否则返回False
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,application/octet-stream",
    }
    
    # 创建临时文件路径
    temp_path = f"{output_path}.download"
    
    for attempt in range(max_retries):
        try:
            # 发起请求
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件大小
            file_size = int(response.headers.get('content-length', 0))
            
            # 检查是否为PDF文件
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'octet-stream' not in content_type and file_size < 10000:
                print(f"警告: {url} 可能不是PDF文件 (content-type: {content_type}, size: {file_size})")
                
                # 检查响应内容的前几个字节是否为PDF签名
                if not response.content.startswith(b'%PDF'):
                    if attempt < max_retries - 1:
                        print(f"尝试重新下载... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                    else:
                        return False
              # 创建进度条
            progress_bar = tqdm.tqdm(
                total=file_size, 
                unit='B', 
                unit_scale=True,
                desc=os.path.basename(output_path)
            )
            
            # 下载文件
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
            progress_bar.close()
            
            # 下载完成后，重命名临时文件
            if os.path.exists(temp_path):
                if os.path.exists(output_path):
                    os.remove(output_path)  # 如果存在同名文件，先删除
                os.rename(temp_path, output_path)
                return True
            
        except requests.exceptions.RequestException as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)  # 清理临时文件
            
            print(f"下载失败 ({url}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"重试下载... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"达到最大重试次数，跳过此文件")
                return False
    
    return False


def get_first_author(authors_str):
    """
    从作者字符串中提取第一作者的姓氏
    """
    if not authors_str:
        return "Unknown"
        
    # 如果有多个作者（用逗号分隔），取第一个
    first_author = authors_str.split(',')[0].strip()
    
    # 取姓氏（假设姓氏是最后一个单词）
    last_name = first_author.split()[-1]
    
    return last_name


def download_papers():
    """
    批量下载论文
    """
    # 创建下载文件夹
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)
        print(f"创建论文保存文件夹: {DOWNLOAD_FOLDER}")
    
    # 读取论文信息和eprint链接
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            papers_data = json.load(f)
        
        print(f"从 {INPUT_FILE} 读取了 {len(papers_data)} 篇论文信息")
        
        # 过滤出有eprint URL的论文
        papers_with_url = {
            title: data for title, data in papers_data.items() 
            if data.get("eprint_url")
        }
        
        print(f"找到 {len(papers_with_url)}/{len(papers_data)} 篇有eprint链接的论文")
        
        # 开始下载
        successful = 0
        failed = 0
        
        for title, data in papers_with_url.items():
            eprint_url = data.get("eprint_url")
            authors = data.get("authors", "")
            
            # 构建文件名
            first_author = get_first_author(authors)
            filename = f"{first_author}-{title}.pdf"
            safe_filename = sanitize_filename(filename)
            output_path = os.path.join(DOWNLOAD_FOLDER, safe_filename)
            
            # 如果文件已存在，则跳过
            if os.path.exists(output_path):
                print(f"跳过已下载的论文: {safe_filename}")
                successful += 1
                continue
            
            # 获取PDF下载链接
            pdf_url = extract_pdf_url_from_eprint_url(eprint_url)
            
            print(f"\n下载论文: {title}")
            print(f"作者: {authors}")
            print(f"eprint URL: {eprint_url}")
            print(f"PDF URL: {pdf_url}")
            print(f"保存为: {safe_filename}")
            
            # 下载PDF
            if download_file(pdf_url, output_path, max_retries=MAX_RETRIES):
                print(f"成功下载: {safe_filename}")
                successful += 1
            else:
                print(f"下载失败: {title}")
                failed += 1
            
            # 延迟，避免请求过于频繁
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
        
        # 总结
        print(f"\n下载完成! 成功: {successful}, 失败: {failed}, 总计: {len(papers_with_url)}")
        if successful > 0:
            print(f"论文已保存到文件夹: {os.path.abspath(DOWNLOAD_FOLDER)}")
        
    except Exception as e:
        print(f"处理论文数据时出错: {str(e)}")


def main():
    """
    主函数
    """
    print("开始批量下载IACR eprint论文...")
    download_papers()


if __name__ == "__main__":
    # 检查需要的依赖
    try:
        import tqdm
    except ImportError:
        print("正在安装必要的依赖...")
        import subprocess
        subprocess.check_call(["pip", "install", "tqdm"])
        print("依赖安装完成")
        import tqdm  # 再次导入，确保可用
    
    main()
