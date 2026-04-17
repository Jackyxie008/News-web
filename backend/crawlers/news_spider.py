"""
通用新闻爬虫 - 使用 Scrapy 框架
可以被其他代码导入使用

用法:
    # 导入使用
    from news_spider import crawl_news, crawl_multiple_news
    
    # 爬取单个URL
    result = crawl_news("https://apnews.com/article/...")
    
    # 爬取多个URL
    results = crawl_multiple_news([
        "https://apnews.com/article/...",
        "https://www.bbc.com/news/...",
        "https://www.reuters.com/..."
    ])
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
import warnings

# 忽略 Scrapy 的一些警告
warnings.filterwarnings('ignore')


# 全局变量存储结果
_global_results = []
_failed_urls = []


class NewsSpider(scrapy.Spider):
    """通用新闻爬虫"""
    
    name = 'news_spider'
    
    def __init__(self, urls: List[str] = None, *args, **kwargs):
        """初始化爬虫"""
        super(NewsSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls or []
        self.results = []
    
    def start_requests(self):
        """开始请求"""
        global _global_results
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                }
            )
    
    def handle_error(self, failure):
        """处理请求错误"""
        global _failed_urls
        _failed_urls.append(failure.request.url)
    
    def detect_source(self, url: str) -> str:
        """检测新闻来源"""
        url_lower = url.lower()
        if 'apnews.com' in url_lower:
            return 'AP News'
        elif 'bbc.com' in url_lower:
            return 'BBC News'
        elif 'reuters.com' in url_lower:
            return 'Reuters'
        elif 'cnn.com' in url_lower:
            return 'CNN'
        elif 'nytimes.com' in url_lower:
            return 'NYTimes'
        else:
            return 'Unknown'
    
    def parse(self, response: Response):
        """解析页面"""
        global _global_results
        
        result = {
            'url': response.url,
            'title': '',
            'publish_time': '',
            'content': ''
        }
        
        # 提取标题
        result['title'] = self.extract_title(response)
        
        # 提取发布时间
        result['publish_time'] = self.extract_publish_time(response)
        
        # 提取正文内容
        result['content'] = self.extract_content(response)
        
        _global_results.append(result)
        self.results.append(result)
        yield result
    
    def extract_title(self, response: Response) -> str:
        """提取标题"""
        # 方法1: 查找 h1 标签
        title = response.css('h1::text').get()
        if title:
            return self.clean_text(title)
        
        # 方法2: 查找 title 标签
        title = response.css('title::text').get()
        if title:
            return self.clean_text(title)
        
        # 方法3: 查找 meta 标签
        title = response.css('meta[property="og:title"]::attr(content)').get()
        if title:
            return self.clean_text(title)
        
        return ''
    
    def extract_publish_time(self, response: Response) -> str:
        """提取发布时间"""
        # 方法1: 查找 time 标签
        publish_time = response.css('time::attr(datetime)').get()
        if publish_time:
            return publish_time
        
        # 方法2: 查找 meta 标签
        publish_time = response.css('meta[property="article:published_time"]::attr(content)').get()
        if publish_time:
            return publish_time
        
        # 方法3: 查找 meta name="date"
        publish_time = response.css('meta[name="date"]::attr(content)').get()
        if publish_time:
            return publish_time
        
        # 方法4: 查找 time 标签的文本内容
        publish_time = response.css('time::text').get()
        if publish_time:
            return self.clean_text(publish_time)
        
        return ''
    
    def extract_author(self, response: Response) -> str:
        """提取作者"""
        # 方法1: 查找 meta author - 如果是URL则跳过
        author = response.css('meta[name="author"]::attr(content)').get()
        if author and not author.startswith('http') and len(author) < 50:
            return self.clean_text(author)
        
        # 方法2: 查找 meta property="article:author"
        author = response.css('meta[property="article:author"]::attr(content)').get()
        if author and not author.startswith('http') and len(author) < 50:
            return self.clean_text(author)
        
        # 方法3: 查找 author 相关 class
        author = response.css('[class*="author"]::text').get()
        if author and not author.startswith('http') and len(author) < 50:
            return self.clean_text(author)
        
        # 方法4: 查找 itemprop="author"
        author = response.css('[itemprop="author"]::text').get()
        if author and not author.startswith('http') and len(author) < 50:
            return self.clean_text(author)
        
        # 方法5: 查找 By 开头的文本
        author = response.css('span::text, a::text').re_first(r'^By\s+(.+)$')
        if author and not author.startswith('http') and len(author) < 50:
            return self.clean_text(author)
        
        return ''
    
    def extract_content(self, response: Response) -> str:
        """提取正文内容"""
        content_parts = []
        
        # 方法1: 查找 article 标签
        article = response.css('article')
        if article:
            paragraphs = article.css('p::text').getall()
            content_parts.extend(paragraphs)
        
        # 方法2: 查找 main 标签
        if not content_parts:
            main = response.css('main')
            if main:
                paragraphs = main.css('p::text').getall()
                content_parts.extend(paragraphs)
        
        # 方法3: 查找包含 article 或 content 的 div
        if not content_parts:
            content_divs = response.css('div[class*="article"], div[class*="content"], div[class*="story"]')
            for div in content_divs:
                paragraphs = div.css('p::text').getall()
                if len(paragraphs) >= 3:
                    content_parts.extend(paragraphs)
                    break
        
        # 方法4: 查找所有段落
        if not content_parts:
            all_p = response.css('p::text').getall()
            # 过滤太短或太长的段落
            valid_p = [p for p in all_p if 50 < len(p) < 1000]
            content_parts.extend(valid_p)
        
        # 清理并合并内容
        if content_parts:
            # 过滤掉太短的段落
            valid_content = [self.clean_text(p) for p in content_parts if len(p) > 20]
            return '\n\n'.join(valid_content)
        
        return ''
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ''
        # 移除多余空白
        text = ' '.join(text.split())
        return text.strip()


def crawl_news(url: str) -> Dict:
    """爬取单个新闻URL
    
    Args:
        url: 新闻链接
        
    Returns:
        Dict: 包含标题、发布时间、作者等字段的字典
    """
    results = crawl_multiple_news([url])
    return results[0] if results else {}


def crawl_multiple_news(urls: List[str]) -> List[Dict]:
    """爬取多个新闻URL
    
    Args:
        urls: 新闻链接列表
        
    Returns:
        List[Dict]: 包含多个新闻数据的列表
    """
    global _global_results, _failed_urls
    
    if not urls:
        return []
    
    # 重置全局结果
    _global_results = []
    _failed_urls = []
    
    # 创建 CrawlerProcess
    process = CrawlerProcess(settings={
        'LOG_LEVEL': 'ERROR',  # 只显示错误
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'ROBOTSTXT_OBEY': False,  # 不遵循 robots.txt
        'CONCURRENT_REQUESTS': 1,  # 串行爬取
        'DOWNLOAD_DELAY': 1,  # 延迟1秒
        'TELNETCONSOLE_ENABLED': False,  # 禁用telnet
        'AUTOTHROTTLE_ENABLED': False,  # 禁用自动限速
    })
    
    # 使用 lambda 来动态创建爬虫
    process.crawl(NewsSpider, urls=urls)
    
    # 运行爬虫
    process.start()
    
    # 返回结果
    return _global_results


def save_to_json(data, output_file):
    """保存数据到JSON文件 - 在原有基础上添加新数据"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 读取原有数据
    existing_data = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        except:
            existing_data = []
    
    # 合并数据（去重）
    existing_urls = set()
    for item in existing_data:
        if isinstance(item, dict) and 'url' in item:
            existing_urls.add(item['url'])
    
    # 添加新数据（去重）
    for item in data:
        if isinstance(item, dict) and 'url' in item:
            if item['url'] not in existing_urls:
                existing_data.append(item)
                existing_urls.add(item['url'])
    
    # 保存合并后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到: {output_file}")


def main():
    """主函数 - 测试用"""
    # 测试URL列表
    test_urls = [
        "https://edition.cnn.com/webview/politics/live-news/trump-indictment-stormy-daniels-news-04-03-23/index.html"
    ]
    
    print("=" * 60)
    print("正在爬取新闻...")
    print("-" * 60)
    
    # 爬取新闻
    results = crawl_multiple_news(test_urls)
    
    # 打印结果
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] 标题: {result.get('title', 'N/A')}")
        print(f"    发布时间: {result.get('publish_time', 'N/A')}")
    
    # 保存到 temp.json
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        'temp.json'
    )
    save_to_json(results, output_file)
    
    print("\n" + "=" * 60)
    print(f"爬取完成! 共获取 {len(results)} 条，获取失败 {len(_failed_urls)} 条")
    if _failed_urls:
        print('失败链接：')
        for url in _failed_urls:
            print(f"    {url}")
    print("=" * 60)


if __name__ == '__main__':
    main()
