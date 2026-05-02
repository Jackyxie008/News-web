# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import re
import json
from datetime import datetime

# 配置信息
LIST_URL = "https://app.modaily.cn/app_if/getArticles?columnId=102&lastFileId=0&page=0&version=0&jsoncallback=angular.callbacks._6"
HEADERS = {
    "Referer": "https://www.modaily.cn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SOURCE_NAME = "Macao_Daily_News"
SOURCE_REPUTATION = 41.75  # 声誉值

# 需要过滤的新闻标题关键词
EXCLUDE_TITLE_KEYWORDS = [
    "澳門日報今日看點",
    "關注澳門日報各大平台 掌握更多資訊",
    "澳門日報重點新聞快遞",
    "澳日體育焦點",
    "【澳日快趣】",
    "【澳門記憶】"
]


def convert_pub_time(pub_time):
    """
    将澳门日报的时间格式转换为标准格式
    输入格式: 2026-05-02 15:11:04:0 或 2026-05-02 14:49:29:882
    输出格式: 2026-05-02 15:11:04
    """
    if not pub_time:
        return pub_time
    # 移除毫秒部分 (冒号后的数字)
    parts = pub_time.rsplit(':', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return pub_time


def get_existing_file_ids_from_db(cursor):
    """从数据库获取已存在的fileId集合"""
    cursor.execute("SELECT link FROM news WHERE source=?", (SOURCE_NAME,))
    file_ids = set()
    for row in cursor.fetchall():
        link = row[0]
        if link:
            # 从链接中提取 fileId，格式如: https://appimg.modaily.cn/app/displayTemplate1/dist/index.html#/newsDetail/9976148/
            match = re.search(r'/newsDetail/(\d+)/', link)
            if match:
                file_ids.add(match.group(1))
    return file_ids


async def fetch_detail(session, detail_url):
    """异步抓取并解析单篇新闻详情"""
    try:
        async with session.get(detail_url, headers=HEADERS, timeout=10) as response:
            if response.status != 200:
                return None
            
            # aiohttp 默认会尝试推测编码，这里手动指定 utf-8 确保不乱码
            html = await response.text(encoding='utf-8')
            data = {}

            # 1. 提取封面图 (og:image)
            img_match = re.search(r'<meta property="og:image" content="(.*?)"', html)
            data["image_url"] = img_match.group(1) if img_match else ""

            # 2. 从 enpproperty 注释块提取元数据
            prop_block = re.search(r'<!--enpproperty (.*?)-->', html, re.S)
            if prop_block:
                block = prop_block.group(1)
                data["article_id"] = re.search(r"<articleid>(.*?)</articleid>", block).group(1) if re.search(r"<articleid>(.*?)</articleid>", block) else ""
                data["title"] = re.search(r"<title>(.*?)</title>", block).group(1) if re.search(r"<title>(.*?)</title>", block) else ""
                data["pub_time"] = re.search(r"<date>(.*?)</date>", block).group(1) if re.search(r"<date>(.*?)</date>", block) else ""
                data["news_url"] = re.search(r"<url>(.*?)</url>", block).group(1) if re.search(r"<url>(.*?)</url>", block) else ""

            # 3. 提取并清洗正文
            content_match = re.search(r'<!--enpcontent-->(.*?)<!--/enpcontent-->', html, re.S)
            if content_match:
                clean_text = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
                data["content"] = clean_text.replace('\n', '').replace('\r', '')
            
            return data
    except Exception as e:
        print(f"解析失败 {detail_url}: {e}")
        return None


async def crawl_macao_daily_news(cursor):
    """
    爬取澳门日报新闻，存储到 data.db
    参数 cursor: 已打开的数据库游标
    """
    # 1. 先从数据库获取已存在的链接
    existing_file_ids = get_existing_file_ids_from_db(cursor)
    
    async with aiohttp.ClientSession() as session:
        # 2. 获取新闻列表
        async with session.get(LIST_URL, headers=HEADERS) as response:
            if response.status != 200:
                print("  获取列表失败")
                return []
            
            list_text = await response.text()
            match = re.search(r'\((\{.*\})\)', list_text)
            if not match:
                print("  解析列表JSON失败")
                return []
            
            # 获取列表中的所有链接
            news_list = json.loads(match.group(1)).get('list', [])[:10]
        
        # 3. 先过滤掉已存在的链接（通过fileId匹配）
        new_items = []
        for item in news_list:
            url = item.get('urlPad')
            file_id = str(item.get('fileId'))  # 统一转换为字符串
            # 通过fileId判断是否已存在
            if url and file_id and file_id not in existing_file_ids:
                new_items.append({'url': url, 'fileId': file_id})
        
        # 4. 如果没有新新闻，直接结束
        if not new_items:
            print("  没有新的新闻需要抓取")
            return []
        
        # 5. 构造异步任务池，只抓取新新闻
        tasks = [fetch_detail(session, item['url']) for item in new_items]
        
        results = await asyncio.gather(*tasks)
        
        # 过滤掉抓取失败的结果
        final_data = [r for r in results if r]
        
        # 过滤掉标题包含指定关键词的新闻
        filtered_data = []
        for news in final_data:
            title = news.get('title', '')
            # 检查标题是否包含需要排除的关键词
            if any(keyword in title for keyword in EXCLUDE_TITLE_KEYWORDS):
                continue
            # 检查正文是否为空
            content = news.get('content', '')
            if not content or len(content.strip()) == 0:
                continue
            filtered_data.append(news)
        
        final_data = filtered_data

        print(f"  爬取完成，成功获取 {len(final_data)} 条澳门日报新闻")
        
        # 6. 准备插入的数据
        news_items = []
        for news in final_data:
            # 转换时间格式，去除毫秒部分
            pub_time = convert_pub_time(news.get('pub_time', ''))
            news_items.append((
                SOURCE_NAME,
                SOURCE_REPUTATION,
                news.get('title', ''),
                news.get('news_url', ''),
                pub_time,
                news.get('content', ''),
                news.get('image_url', '')
            ))
        
        return news_items


if __name__ == "__main__":
    import sqlite3
    from pathlib import Path
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 确保表存在
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            reputation INTEGER,
            title TEXT,
            link TEXT UNIQUE,
            published TEXT,
            full_text TEXT,
            image_url TEXT
        )
    ''')
    conn.commit()
    
    news_items = asyncio.run(crawl_macao_daily_news(cursor))
    
    if news_items:
        # 使用 INSERT OR IGNORE 遇到唯一约束冲突自动跳过
        cursor.executemany('''
            INSERT OR IGNORE INTO news (source, reputation, title, link, published, full_text, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', news_items)
        inserted = cursor.rowcount
        conn.commit()
        print(f"  数据库插入完成，新增加 {inserted} 条新闻")
    
    conn.close()