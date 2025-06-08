import os
import json
from bs4 import BeautifulSoup

def extract_papers(html_file_path):
    """
    从Eurocrypt 2025 HTML文件中提取所有论文题目和作者信息
    """
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有论文项
    paper_items = soup.find_all('li')
    
    papers = []
    
    for item in paper_items:
        # 查找标题元素
        title_elem = item.find('h5', class_='paperTitle')
        if not title_elem:
            continue
            
        title = title_elem.get_text(strip=True)
        
        # 查找作者和机构信息
        author_elem = title_elem.find_next('p')
        if not author_elem:
            continue
            
        # 提取作者信息（排除<br>和<small>标签内容）
        authors_text = ''
        for content in author_elem.contents:
            if content.name != 'br' and content.name != 'small':
                authors_text += content.strip()
        
        # 提取机构信息
        affiliation_elem = author_elem.find('small', class_='fst-italic')
        affiliation = affiliation_elem.get_text(strip=True) if affiliation_elem else ''
        
        # 添加到论文列表
        papers.append({
            'title': title,
            'authors': authors_text,
            'affiliation': affiliation
        })
    
    return papers

def save_to_json(papers, output_file):
    """
    将论文列表保存为JSON文件
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'papers': papers}, f, ensure_ascii=False, indent=2)
    
    print(f"已提取 {len(papers)} 篇论文并保存到 {output_file}")

if __name__ == "__main__":
    # 文件路径
    html_file = "Eurocrypt 2025 Accepted Papers.html"
    output_json = "eurocrypt_2025_papers.json"
    
    # 确保使用当前目录的路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, html_file)
    output_path = os.path.join(current_dir, output_json)
    
    # 提取论文并保存为JSON
    papers = extract_papers(html_path)
    save_to_json(papers, output_path)
