# -*- coding: utf-8 -*-

import asyncio          # 异步协程，并发爬取/请求
import aiohttp          # 异步HTTP客户端，发网络请求
import feedparser       # 解析 RSS / XML 订阅源（就是你刚才看的那种XML）
import trafilatura      # 提取网页正文（自动去广告、导航栏）
from datetime import datetime, timezone  # 处理时间、时区
from pathlib import Path  # 处理文件路径（跨平台）
import re               # 正则表达式，清洗文本、匹配内容
import json             # 读写JSON格式数据
import sqlite3          # 轻量级数据库，存爬取结果
from dateutil import parser  # 智能解析各种时间字符串


def extract_image_url(entry):
    """
    从 RSS 条目中提取最佳图片 URL
    按优先级尝试: media_content > media_thumbnail > enclosures > summary中的img标签
    """
    # 1. media:content 或 media:thumbnail (CNN/路透社/BBC等标准格式)
    media = entry.get('media_content') or entry.get('media_thumbnail')
    if media:
        if isinstance(media, list) and len(media) > 0:
            # 如果有多个图片，选择尺寸最大的
            best = max(media, key=lambda x: int(x.get('width', 0)) * int(x.get('height', 0)))
            return best.get('url')
        elif isinstance(media, dict):
            return media.get('url')
    
    # 2. enclosures (某些 RSS 源用 enclosure 标签传图片)
    enclosures = entry.get('enclosures') or []
    for enc in enclosures:
        if isinstance(enc, dict) and enc.get('type', '').startswith('image/'):
            return enc.get('url')
    
    # 3. summary 中的 img 标签
    summary = entry.get('summary') or entry.get('description') or ''
    if summary:
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary, re.IGNORECASE)
        if img_match:
            return img_match.group(1)
    
    return None


def normalize_published_time(time_str):
    """
    统一标准化发布时间格式
    支持解析各种RSS时间格式，统一转换为北京时间 YYYY-MM-DD HH:MM:SS 格式
    """
    if not time_str:
        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        dt = parser.parse(time_str)
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


async def fetch(session, url):
    """异步获取网页内容"""
    try:
        async with session.get(url, timeout=90, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,*/*;q=0.8"}) as resp:
            if resp.status != 200:
                return None
            return await resp.text()
    except Exception as e:
        print(f"Fetch error {url}: {e}")
        return None


async def process_entry(session, entry, source, authority):
    """处理单个RSS条目，提取新闻详情"""
    link = entry.get("link")
    if not link:
        return None

    html = await fetch(session, link)
    if not html:
        return None

    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, trafilatura.extract, html)

    # 提取RSS原生图片
    img_url = extract_image_url(entry)

    return {
        "source": source,
        "authority": authority,
        "title": entry.get("title"),
        "link": link,
        "published": normalize_published_time(entry.get("published") or entry.get("updated")),
        "full_text": text or "[提取失败]",
        "image_url": img_url
    }


async def process_rss_source(session, rss_url, source, authority, content_can_be_crawled):
    """异步处理单个RSS源"""
    print(f"  爬取 URL: {rss_url}")
    
    rss_text = await fetch(session, rss_url)
    if not rss_text:
        print(f"  获取 RSS 源失败: {rss_url}")
        return []
    
    feed = feedparser.parse(rss_text)
    if feed.bozo:
        print(f"  RSS parse error: {feed.bozo_exception}")
        return []
    
    all_items = []
    
    entries_to_process = feed.entries[:10] # 每个源只处理最新的10条
    
    if content_can_be_crawled:
        tasks = [process_entry(session, entry, source, authority) for entry in entries_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if not isinstance(res, Exception) and res:
                all_items.append(res)
    else:
        for entry in entries_to_process:
            text = trafilatura.extract(entry.get("summary") or entry.get("description"))
            
            # 提取RSS原生图片
            img_url = extract_image_url(entry)
            
            all_items.append({
                "source": source,
                "authority": authority,
                "title": entry.get("title"),
                "link": entry.get("link"),
                "published": normalize_published_time(entry.get("published") or entry.get("updated")),
                "full_text": text or "[提取失败]",
                "image_url": img_url
            })

    return all_items


async def crawler():
    """
    主函数：读取 feeds.json，爬取每个 RSS 源，直接插入数据库
    """
    feeds_file = Path("backend/crawlers/feeds.json")
    if not feeds_file.exists():
        print(f"配置文件不存在: {feeds_file}")
        return

    with open(feeds_file, "r", encoding="utf-8") as f:
        feeds = json.load(f)

    async with aiohttp.ClientSession() as session:
        all_tasks = []
        
        for feed_config in feeds:
            if not feed_config.get("crawl", True):
                print(f"跳过的源: {feed_config.get('source')}")
                continue

            source = feed_config.get("source")
            authority = feed_config.get("authority", 0)
            urls = feed_config.get("rss_url")
            content_can_be_crawled = feed_config.get("content_can_be_crawled", True)
            
            if not source or not urls:
                print(f"跳过无效配置: {feed_config}")
                continue

            for rss_url in urls:
                task = process_rss_source(session, rss_url, source, authority, content_can_be_crawled)
                all_tasks.append(task)

        sem = asyncio.Semaphore(5)
        
        async def bounded_task(task_func):
            async with sem:
                return await task_func
        
        bounded_tasks = [bounded_task(task) for task in all_tasks]
        
        print(f"开始爬取，共 {len(bounded_tasks)} 个RSS源，最大并发数: 5")
        
        results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        all_news = []
        for result in results:
            if not isinstance(result, Exception) and result:
                all_news.extend(result)
        
        print(f"\n✅ 爬取完成，总共获取 {len(all_news)} 条新闻")
        
        # 直接批量插入数据库
        db_path = Path("backend/data/data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 确保表存在，第一次运行自动创建
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                authority INTEGER,
                title TEXT,
                link TEXT UNIQUE,
                published TEXT,
                full_text TEXT,
                image_url TEXT
            )
        ''')
        conn.commit()
        
        # 先批量查询所有链接，过滤已经存在的新闻
        all_links = [item['link'] for item in all_news]
        placeholders = ','.join(['?'] * len(all_links))
        
        cursor.execute(f"SELECT link FROM news WHERE link IN ({placeholders})", all_links)
        existing_links = set(row[0] for row in cursor.fetchall())
        
        # 内存层先去重 同一批次内相同link只保留一个
        seen_links = set()
        unique_items = []
        for item in all_news:
            if item['link'] not in existing_links and item['link'] not in seen_links:
                seen_links.add(item['link'])
                unique_items.append((
                    item['source'],
                    item['authority'],
                    item['title'],
                    item['link'],
                    item['published'],
                    item['full_text'],
                    item['image_url']
                ))
        
        # 使用 INSERT OR IGNORE 遇到唯一约束冲突自动跳过 不抛出错误
        cursor.executemany('''
            INSERT OR IGNORE INTO news (source, authority, title, link, published, full_text, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', unique_items)
        
        # 获得实际成功插入的行数
        inserted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ 数据库插入完成，新增加 {inserted} 条新闻，重复 {len(all_news) - inserted} 条")

if __name__ == "__main__":
    asyncio.run(crawler())