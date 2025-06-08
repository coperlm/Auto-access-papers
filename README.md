# IACR Eprint论文获取与下载工具

这是一套用于自动获取和下载IACR Eprint论文的Python工具集，专为Eurocrypt 2025会议论文设计，但也可轻松扩展到其他密码学会议。

## 功能概述

此工具集提供以下功能：

1. **提取会议论文信息**：从会议网页提取论文标题、作者等信息
2. **获取Eprint链接**：自动在IACR搜索引擎上查找每篇论文对应的Eprint链接
3. **批量下载论文**：基于获取到的Eprint链接，自动下载PDF文件并以有意义的方式重命名

## 文件说明

- `eurocrypt_2025_papers.json` - 包含所有Eurocrypt 2025论文的信息
- `get_eprint_urls.py` - 用于获取论文的Eprint链接并保存到JSON文件
- `download_eprint_papers.py` - 用于批量下载论文PDF
- `paper_eprint_urls.json` - 保存论文与对应Eprint链接的映射关系
- `papers/` - 下载的论文存放目录
- `search_results/` - 保存IACR搜索结果的HTML文件（用于调试）

## 使用方法

### 1. 获取论文Eprint链接

```bash
# 基本用法
python get_eprint_urls.py

# 高级用法
python get_eprint_urls.py --start 0 --end 10  # 只处理前10篇论文
python get_eprint_urls.py --no-headless        # 显示浏览器窗口
python get_eprint_urls.py --retry-failed       # 重试之前失败的论文
```

### 2. 下载论文PDF

```bash
python download_eprint_papers.py
```

下载的论文将保存在`papers/`目录中，文件名格式为`[作者姓氏]-[论文标题].pdf`。

## 技术细节

### 获取Eprint链接 (`get_eprint_urls.py`)

该脚本使用Selenium进行浏览器自动化，主要流程：

1. 读取论文信息
2. 构建搜索查询（标题+第一作者）
3. 使用Selenium访问IACR搜索页面
4. 等待页面加载并渲染JavaScript内容
5. 从渲染后的HTML中提取eprint链接
6. 保存结果到JSON文件

支持多种备用机制以提高链接提取成功率：
- 多种CSS选择器尝试
- 滚动页面以触发动态加载
- 正则表达式匹配

### 下载论文PDF (`download_eprint_papers.py`)

该脚本接收eprint链接并下载PDF文件，主要流程：

1. 读取`paper_eprint_urls.json`获取eprint链接
2. 为每篇论文构建下载链接（URL + .pdf）
3. 使用请求库下载PDF文件
4. 显示下载进度条
5. 自动重试失败的下载
6. 将文件以作者-标题的方式命名并保存

## 依赖项

- Python 3.6+
- requests
- selenium
- webdriver-manager
- tqdm
- BeautifulSoup4

可以使用以下命令安装所需依赖：

```bash
pip install requests selenium webdriver-manager tqdm beautifulsoup4
```

## 调整与扩展

### 自定义搜索行为

在`get_eprint_urls.py`中，您可以调整以下参数：
- 搜索延迟时间
- 浏览器设置
- 多种CSS选择器

### 自定义下载行为

在`download_eprint_papers.py`中，您可以调整以下参数：
- `DOWNLOAD_FOLDER` - 下载文件保存位置
- `MAX_RETRIES` - 下载失败时的最大重试次数
- `DELAY_BETWEEN_DOWNLOADS` - 两次下载之间的延迟

## 提示

1. 如果链接获取过程中遇到问题，可以使用`--no-headless`选项查看浏览器操作过程
2. 对于特别难找到的论文，可以查看`search_results/`目录下保存的HTML文件并手动添加链接
3. 下载过程已设计为可中断和继续，已下载的文件不会重复下载

## 版权说明

此工具仅用于学术研究目的。请尊重论文作者的知识产权，遵守IACR eprint的使用条款。

---

*最后更新: 2025年6月8日*
