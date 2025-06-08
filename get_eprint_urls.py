import json
import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_webdriver(use_headless=True):
    """
    设置Selenium WebDriver
    
    Args:
        use_headless: 是否使用无头模式，默认为True
    """
    options = Options()
    if use_headless:
        options.add_argument("--headless")  # 无头模式，不显示浏览器窗口
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    
    # 添加用户代理 - 使用更现代的用户代理
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 设置preferences以改进网页渲染
    prefs = {
        "profile.default_content_setting_values.notifications": 2,  # 阻止通知
        "profile.managed_default_content_settings.images": 1,  # 允许加载图片
        "profile.default_content_setting_values.cookies": 1,  # 允许cookies
        "profile.managed_default_content_settings.javascript": 1  # 允许JavaScript
    }
    options.add_experimental_option("prefs", prefs)
    
    # 使用webdriver_manager自动安装并管理ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # 设置页面加载超时
    driver.set_page_load_timeout(30)
    
    return driver

def get_eprint_url(title, authors="", driver=None):
    """
    使用IACR搜索论文的eprint链接并返回
    """
    # 为搜索结果创建文件夹
    search_results_dir = "search_results"
    if not os.path.exists(search_results_dir):
        os.makedirs(search_results_dir)
    
    # 构建搜索查询
    query = title
    if authors:
        first_author = authors.split(',')[0].strip()
        query = f"{query} {first_author}"
    
    # 向IACR发起搜索
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://iacr.org/search/?q={encoded_query}"
    
    print(f"搜索: {title}")
    print(f"IACR搜索URL: {search_url}")
    
    # 获取安全的文件名（用于保存HTML）
    safe_title = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in title)
    safe_title = safe_title[:50]  # 限制长度
    html_file = os.path.join(search_results_dir, f"{safe_title}.html")
    
    need_to_close_driver = False
    try:
        # 如果没有传入driver，则创建一个新的
        if driver is None:
            driver = setup_webdriver()
            need_to_close_driver = True
          # 使用Selenium访问搜索页面
        driver.get(search_url)
        
        # 等待页面加载完成（等待任何搜索结果元素出现）
        page_loaded = False
        selectors_to_try = [".gs_ri", ".gsc-result", ".gs_r", "div.result", "div.search-result"]
        
        for selector in selectors_to_try:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"页面加载完成，找到选择器: {selector}")
                page_loaded = True
                break
            except:
                continue
                
        if not page_loaded:
            print("页面加载超时，尝试使用当前内容继续处理...")
          # 等待JavaScript执行完成并尝试滚动页面以加载更多内容
        time.sleep(3)
        
        # 执行滚动脚本以确保加载所有内容
        try:
            driver.execute_script("""
                // 滚动到底部
                window.scrollTo(0, document.body.scrollHeight);
                // 滚动回顶部
                setTimeout(function() { window.scrollTo(0, 0); }, 1000);
                // 再次滚动到中间位置
                setTimeout(function() { window.scrollTo(0, document.body.scrollHeight/2); }, 2000);
            """)
            time.sleep(2)  # 等待滚动和可能的内容加载完成
        except Exception as e:
            print(f"执行滚动脚本时出错：{str(e)}")
        
        # 获取渲染后的HTML
        rendered_html = driver.page_source
        
        # 保存HTML到文件
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        
        print(f"渲染后的搜索结果已保存到: {html_file}")
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(rendered_html, 'html.parser')
          # 尝试找到所有搜索结果条目，使用多种可能的CSS选择器
        for selector in [".gs_ri", ".gsc-result", ".gs_r", "div.result", "div.search-result"]:
            result_items = soup.select(selector)
            if result_items:
                print(f"找到 {len(result_items)} 个搜索结果（使用选择器: {selector}）")
                break
        
        # 如果使用预定义选择器找不到结果，尝试查找所有可能包含链接的区域
        if not result_items:
            # 查找所有含有标题样式的元素
            potential_results = soup.select("h3, h2, .title, .result-title")
            if potential_results:
                print(f"使用备用方法找到 {len(potential_results)} 个潜在结果元素")
                result_items = []
                # 对于每个标题元素，获取其父元素作为结果项
                for elem in potential_results:
                    if elem.parent:
                        result_items.append(elem.parent)
        
        if result_items:
            # 遍历搜索结果，查找eprint链接
            for item in result_items:
                # 获取结果标题
                for title_selector in [".gs_rt", "h3", "h2", ".title", ".result-title"]:
                    result_title = item.select_one(title_selector)
                    if result_title:
                        result_title_text = result_title.get_text(strip=True)
                        print(f"检查结果: {result_title_text}")
                        break
                
                # 查找链接 - 先在当前项中查找
                links = item.select("a")
                for link in links:
                    href = link.get('href', '')
                    # 检查是否为eprint链接
                    if 'eprint.iacr.org' in href:
                        eprint_url = href
                        print(f"找到eprint链接: {eprint_url}")
                        return eprint_url
            
            # 如果在结果项中没找到，尝试查找整个页面中的所有链接
            all_links = soup.select("a")
            print(f"在整个页面中查找，共有 {len(all_links)} 个链接")
            for link in all_links:
                href = link.get('href', '')
                if 'eprint.iacr.org' in href:
                    eprint_url = href
                    print(f"在页面全局范围内找到eprint链接: {eprint_url}")
                    return eprint_url
          # 如果使用BeautifulSoup没有找到链接，尝试更广泛的正则表达式搜索
        eprint_patterns = [
            re.compile(r'(https?://eprint\.iacr\.org/\d{4}/\d{1,4})'),  # 标准eprint链接
            re.compile(r'href="(https?://eprint\.iacr\.org/\d{4}/\d{1,4})"'),  # 带href的链接
            re.compile(r'href=["\'](https?://eprint\.iacr\.org/\d{4}/\d{1,4})["\']'),  # 各种引号的href
            re.compile(r'url=(https?://eprint\.iacr\.org/\d{4}/\d{1,4})'),  # 重定向链接
        ]
        
        for pattern in eprint_patterns:
            matches = pattern.findall(rendered_html)
            if matches:
                eprint_url = matches[0]
                print(f"通过正则表达式找到eprint链接: {eprint_url}")
                return eprint_url
        
        # 如果还是找不到，尝试在页面源码中搜索eprint关键字周围的内容
        if 'eprint.iacr.org' in rendered_html:
            print("页面中存在eprint.iacr.org，但未能提取出完整链接，尝试人工检查HTML")
            # 可以保存一个标记的文件，以便后续人工检查
            with open(os.path.join(search_results_dir, f"{safe_title}_needs_check.txt"), 'w', encoding='utf-8') as f:
                f.write(f"页面包含eprint.iacr.org但未能自动提取链接，请手动检查HTML文件: {html_file}")
        
        print(f"未找到eprint链接: {title}")
        return None
        
    except Exception as e:
        print(f"搜索出错 ({title}): {str(e)}")
        return None
    
    finally:
        # 如果是在这个函数中创建的driver，则关闭它
        if need_to_close_driver and driver:
            driver.quit()

def process_papers_from_json(use_headless=True, start_index=0, end_index=None, retry_failed=False):
    """
    处理论文JSON文件，提取eprint链接
    
    Args:
        use_headless: 是否使用无头模式，默认为True
        start_index: 开始处理的论文索引，默认从0开始
        end_index: 结束处理的论文索引（不包含），默认处理到最后
        retry_failed: 是否重试之前失败的论文，默认为False
    """
    # 读取论文JSON文件
    json_file = "eurocrypt_2025_papers.json"
    output_file = "paper_eprint_urls.json"
    
    # 检查是否已有处理过的结果
    result_dict = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                result_dict = json.load(f)
            print(f"加载已有结果, 共 {len(result_dict)} 篇论文")
        except Exception as e:
            print(f"读取已有结果出错: {str(e)}")
            result_dict = {}
    
    try:
        # 创建一个WebDriver实例，供所有搜索共享
        driver = setup_webdriver(use_headless=use_headless)
        
        # 读取论文数据
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        papers = data.get("papers", [])
        total_papers = len(papers)
        print(f"读取了 {total_papers} 篇论文")
        
        # 设置结束索引（如果未指定）
        if end_index is None or end_index > total_papers:
            end_index = total_papers
            
        # 输出处理范围
        print(f"将处理论文 {start_index+1} 到 {end_index} (共 {end_index-start_index} 篇)")        # 处理每篇论文
        for i, paper in enumerate(papers[start_index:end_index], start=start_index):
            title = paper.get("title")
            authors = paper.get("authors", "")
            
            # 检查是否需要跳过已处理的论文
            skip_paper = False
            if not retry_failed and title in result_dict:
                if "eprint_url" in result_dict[title] and result_dict[title]["eprint_url"]:
                    print(f"跳过已处理的论文 ({i+1}/{total_papers}): {title}")
                    skip_paper = True
                elif retry_failed == False:
                    print(f"跳过未找到链接的论文 ({i+1}/{total_papers}): {title}")
                    skip_paper = True
            
            if skip_paper:
                continue
                
            print(f"\n处理论文 {i+1}/{total_papers}: {title}")
            
            # 尝试获取eprint URL，最多尝试2次
            max_attempts = 2
            eprint_url = None
            
            for attempt in range(max_attempts):
                if attempt > 0:
                    print(f"第 {attempt+1} 次尝试...")
                    time.sleep(3)  # 重试前等待
                    
                # 获取eprint URL（传入共享的driver实例）
                eprint_url = get_eprint_url(title, authors, driver=driver)
                
                # 如果成功获取到URL，则跳出重试循环
                if eprint_url:
                    break
            
            # 保存结果
            result_dict[title] = {
                "title": title,
                "authors": authors,
                "eprint_url": eprint_url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 每处理一篇论文，立即保存结果
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result_dict, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"保存结果时出错: {str(e)}")
            
            # 延时，避免请求过于频繁
            delay_time = 5 + (i % 3)  # 稍微随机化延迟时间，避免规律性请求
            print(f"等待 {delay_time} 秒...")
            time.sleep(delay_time)
        
        print("\n所有论文处理完成")
        print(f"结果已保存到 {output_file}")
        
    except Exception as e:
        print(f"处理论文出错: {str(e)}")
    
    finally:
        # 完成后关闭WebDriver
        if 'driver' in locals() and driver:
            driver.quit()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='从IACR搜索获取论文的eprint链接')
    parser.add_argument('--no-headless', action='store_true', help='不使用无头模式（显示浏览器窗口）')
    parser.add_argument('--start', type=int, default=0, help='开始处理的论文索引（从0开始）')
    parser.add_argument('--end', type=int, default=None, help='结束处理的论文索引（不包含）')
    parser.add_argument('--retry-failed', action='store_true', help='重试之前失败的论文')
    
    args = parser.parse_args()
    
    process_papers_from_json(
        use_headless=not args.no_headless,
        start_index=args.start,
        end_index=args.end,
        retry_failed=args.retry_failed
    )
