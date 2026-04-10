# -*- coding: utf-8 -*-

import asyncio  # 异步编程库，用于并发处理
import aiohttp  # 异步 HTTP 客户端库
import feedparser  # RSS/Atom 解析库
import trafilatura  # 网页正文提取库（自动去除广告等噪音）
from datetime import datetime, timezone  # 日期时间处理
from pathlib import Path
import pandas as pd
import re
import json
from crawlers.functions import deduplicate_news_list


async def fetch(session, url):
    """
    异步获取网页内容
    
    Args:
        session: aiohttp 会话对象
        url: 要获取的网页 URL
    
    Returns:
        str: 网页 HTML 内容，失败返回 None
    """
    try:
        # 设置 20 秒超时，使用自定义 User-Agent
        async with session.get(url, timeout=20, headers={"User-Agent": "PersonalNewsBot/1.0"}) as resp:
            if resp.status != 200:
                return None  # 非 200 状态码返回 None
            return await resp.text()  # 返回网页文本内容
    except Exception as e:
        print(f"Fetch error {url}: {e}")  # 打印错误信息
        return None

async def process_entry(session, entry, source, authority):
    """
    处理单个 RSS 条目，提取新闻详情
    
    Args:
        session: aiohttp 会话对象
        entry: RSS 条目字典
        source: 新闻源名称
    
    Returns:
        dict: 包含新闻详情的字典，失败返回 None
    """
    # 获取新闻链接
    link = entry.get("link")
    if not link:
        return None

    # 获取新闻页面 HTML
    html = await fetch(session, link)
    if not html:
        return None

    # 使用 trafilatura 提取网页正文内容（自动去除广告、导航等噪音）
    # 两种方式：直接从 URL 获取或从已下载的 HTML 提取
    downloaded = trafilatura.fetch_url(link)  # 从 URL 直接获取
    text = trafilatura.extract(downloaded or html)  # 提取正文

    # 在 summary_text 中提取图片链接
    summary_text = entry.get("summary") or entry.get("description")
    img_url = None
    if summary_text:
        # 匹配 HTML img 标签中的 src 属性
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary_text)
        if img_match:
            img_url = img_match.group(1)

    # 构建新闻数据字典
    return {
        "source": source,  # 新闻源
        "authority": authority,  # 权威度
        "title": entry.get("title"),  # 标题
        "link": link,  # 原文链接
        "published": entry.get("published") or entry.get("updated"),  # 发布时间
        "full_text": text or "[提取失败]",  # 正文内容，提取失败时标记
        "image_url": img_url  # 图片链接
    }

# 主爬虫函数
async def process_rss_source(session, rss_url, source, authority, content_can_be_crawled):
    """异步处理单个RSS源"""
    print(f"  爬取 URL: {rss_url}")
    
    # 获取 RSS 源内容
    rss_text = await fetch(session, rss_url)
    if not rss_text:
        print(f"  获取 RSS 源失败: {rss_url}")
        return []
    
    # 解析 RSS 内容
    feed = feedparser.parse(rss_text)
    if feed.bozo:
        print(f"  RSS parse error: {feed.bozo_exception}")
        return []
    
    all_items = []
    
    # 限制只处理前10个条目
    entries_to_process = feed.entries[:10]  # 只取前10个条目
    
    if content_can_be_crawled:
        # 创建处理任务（提取正文）
        tasks = [process_entry(session, entry, source, authority) for entry in entries_to_process]
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for res in results:
            if not isinstance(res, Exception) and res:
                all_items.append(res)
    else:
        # 不提取正文，只保存基础信息
        for entry in entries_to_process:  # 只处理前20个条目
            text = trafilatura.extract(entry.get("summary") or entry.get("description"))
            summary_text = entry.get("summary") or entry.get("description")
            img_url = None
            if summary_text:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary_text)
                if img_match:
                    img_url = img_match.group(1)
            all_items.append({
                "source": source,
                "authority": authority,
                "title": entry.get("title"),
                "link": entry.get("link"),
                "published": entry.get("published") or entry.get("updated"),
                "full_text": text or "[提取失败]",
                "image_url": img_url
            })

    return all_items

def save_to_csv(data, csv_file):
    """将数据保存到CSV文件"""
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False, encoding='utf-8')

def load_from_csv(csv_file):
    """从CSV文件加载数据"""
    if not csv_file.exists():
        return []
    
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
        return df.to_dict('records')
    except Exception as e:
        print(f"读取 CSV 文件失败: {e}")
        return []

async def crawler():
    """
    主函数：读取 feeds.json，爬取每个 RSS 源，保存结果到指定目录
    """
    # 读取 feeds.json 配置文件
    feeds_file = Path("backend/crawlers/feeds.json")
    if not feeds_file.exists():
        print(f"配置文件不存在: {feeds_file}")
        return

    with open(feeds_file, "r", encoding="utf-8") as f:
        feeds = json.load(f)

    # 创建输出目录
    output_dir = Path("backend/data/data_categorized_by_media/previous")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 创建异步 HTTP 会话
    async with aiohttp.ClientSession() as session:
        # 收集所有需要处理的RSS源
        all_tasks = []
        source_configs = {}
        
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

            # 将所有RSS源的任务收集到一个列表中
            for rss_url in urls:
                task = process_rss_source(session, rss_url, source, authority, content_can_be_crawled)
                all_tasks.append(task)
                
                # 记录每个任务对应的source信息，用于后续分组保存
                if source not in source_configs:
                    source_configs[source] = {
                        "content_can_be_crawled": content_can_be_crawled,
                        "all_items": []
                    }

        # 将所有任务分成每组5个的批次
        for i in range(0, len(all_tasks), 5):
            batch_tasks = all_tasks[i:i+5]  # 取当前批次的5个任务
            print(f"处理第 {i//5 + 1} 批 RSS 源，共 {len(batch_tasks)} 个")
            
            # 并发执行当前批次的所有RSS源爬取（不分报社）
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理结果，按source分组
            for result in results:
                if not isinstance(result, Exception) and result:
                    # 根据source将结果分组
                    for item in result:
                        source = item.get("source")
                        if source in source_configs:
                            source_configs[source]["all_items"].append(item)
            
            # 去重
            for source, config in source_configs.items():
                all_items = config["all_items"]
                if all_items:  # 只有当有新闻时才去重
                    unique_items, duplicates_count = deduplicate_news_list(all_items)
                    if duplicates_count > 0:
                        config["all_items"] = unique_items
            
            # 如果不是最后一批，添加延迟
            if i + 5 < len(all_tasks):
                await asyncio.sleep(1)  # 批次间延迟1秒

        # 保存每个source的结果
        for source, config in source_configs.items():
            all_items = config["all_items"]
            content_can_be_crawled = config["content_can_be_crawled"]
            
            print(f"正在处理 RSS 源: {source}")
            
            # 保存结果到指定文件
            output_file = output_dir / f"{source}.csv"
            
            # 读取 previous 文件进行比较
            previous_file = output_dir / f"{source}.csv"
            previous_items = load_from_csv(previous_file)
            
            # 提取 previous 文件中的链接集合
            previous_links = {item.get("link") for item in previous_items if item.get("link")}
            
            # 筛选出新内容
            new_items = [item for item in all_items if item.get("link") not in previous_links]
            
            # 新内容保存到 backend/data/data_categorized_by_media/{source}.csv
            new_output_file = Path("backend/data/data_categorized_by_media") / f"{source}.csv"
            save_to_csv(new_items, new_output_file)
            
            # 覆盖 previous 文件
            save_to_csv(all_items, previous_file)
            
            print(f"  爬文章：{len(all_items)} 篇，存到 {output_file}")
            print(f"  新文章：{len(new_items)} 篇，存到 {new_output_file}")

if __name__ == "__main__":

    asyncio.run(crawler())