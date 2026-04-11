import asyncio
import os
import json
import httpx
import aiosqlite
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DB_PATH = Path("backend/data/data.db")

# API 配置映射
PLATFORMS = {
    "zhi_pu": {
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "key": os.getenv("GLM_API_KEY"),
        "model": "GLM-4.7-Flash",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    },
    "silicon": {
        "url": "https://api.siliconflow.cn/v1/chat/completions",
        "key": os.getenv("SILICONFLOW_API_KEY"),
        "model": "Qwen/Qwen3.5-4B",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    }
}

# 地图并发锁（依然保持 1，保护 IP）
map_semaphore = asyncio.Semaphore(1)

async def get_grouped_news(conn, id):
    """
    根据分组ID获取聚合新闻
    参数:
        conn: 全局数据库连接
        id: grouped_news表中的分组ID
    返回:
        (titles_text, contents_text, news_count): 
            titles_text: 合并后的标题字符串
            contents_text: 合并后的正文字符串
            news_count: 该分组对应的新闻ID总数量(int)
    """
    # 1. 查询分组对应的新闻ID列表
    cursor = await conn.execute(
        "SELECT news_id FROM grouped_news WHERE id = ?",
        (id,)
    )
    row = await cursor.fetchone()
    
    if not row or not row[0]:
        return "", "", 0
    
    news_ids_str = row[0]
    news_ids = [int(nid.strip()) for nid in news_ids_str.split(',') if nid.strip().isdigit()]
    
    if not news_ids:
        return "", "", 0
    
    # 2. 按authority从高到低排序，取前5条新闻
    placeholders = ','.join(['?'] * len(news_ids))
    query = f"""
        SELECT title, full_text 
        FROM news 
        WHERE id IN ({placeholders}) 
        ORDER BY authority DESC 
        LIMIT 5
    """
    
    cursor = await conn.execute(query, news_ids)
    rows = await cursor.fetchall()
    
    # 3. 合并标题和正文
    titles = []
    contents = []
    
    for title, full_text in rows:
        if title:
            titles.append(title.strip())
        if full_text:
            # 每条正文只取前2000个字符
            cleaned_text = full_text.strip()
            if len(cleaned_text) > 2000:
                cleaned_text = cleaned_text[:2000] + "..."
            contents.append(cleaned_text)
    
    titles_text = '\n\n'.join(titles)
    contents_text = '\n\n'.join(contents)
    
    return titles_text, contents_text, len(news_ids)

async def get_coordinates(client, location):
    """地理编码：带缓存和频率限制"""
    if not location: return None, None
    async with map_semaphore:
        try:
            headers = {"User-Agent": "NewsMap/1.0"}
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": location, "format": "json", "limit": 1},
                headers=headers,
                timeout=15
            )
            await asyncio.sleep(1.1) # 严格遵守OSM使用协议 每秒最多1次请求
            
            if resp.status_code == 403:
                print("\n\033[91m🚨 严重警告: OpenStreetMap API 返回403 你的IP已经被临时封禁！")
                print("🚨 请立即停止程序，至少等待2小时后再运行，否则封禁时间会延长\033[0m\n")
                return None, None
            
            if resp.status_code == 429:
                print("\033[93m⚠️ OSM 请求频率超限 额外等待5秒\033[0m")
                await asyncio.sleep(5)
                return None, None
            
            if resp.status_code != 200:
                print(f"\033[93m⚠️ OSM 请求失败 状态码: {resp.status_code}\033[0m")
                return None, None
            
            data = resp.json()
            if data:
                return data[0]["lat"], data[0]["lon"]
            
        except Exception as e:
            print(f"\033[93m⚠️ 地理编码请求异常: {str(e)[:60]}\033[0m")
            
    return None, None

async def get_all_unprocessed_ids(conn):
    """获取数据库中所有未处理的分组ID"""
    cursor = await conn.execute(
        "SELECT id FROM grouped_news WHERE latitude IS NULL OR latitude = '' ORDER BY id ASC"
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]

def clean_json_response(text):
    """
    清洗大模型返回的JSON内容 处理各种常见格式问题:
    1. 去掉markdown ```json 代码块标记
    2. 去掉前后空白和换行
    3. 提取最外层{}包裹的有效内容
    """
    if not text:
        return "{}"
    
    original = text
    
    # 1. 移除markdown代码块标记
    if "```json" in text.lower():
        text = text.lower().split("```json", 1)[1]
    if "```" in text:
        text = text.split("```", 1)[0]
    
    # 2. 清理空白
    text = text.strip()
    
    # 3. 定位最外层JSON对象边界
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    
    return text

async def update_grouped_news(conn, news_id, data):
    """更新分组新闻到数据库"""
    fields = []
    values = []
    
    for key, val in data.items():
        fields.append(f"{key} = ?")
        values.append(val)
    
    values.append(news_id)
    
    query = f"UPDATE grouped_news SET {', '.join(fields)} WHERE id = ?"
    await conn.execute(query, values)
    await conn.commit()

async def worker(name, queue, client, db_conn):
    """消费者工人：支持跨平台失败重试"""
    # 自动根据Worker名称匹配平台（通用适配任意数量平台）
    # 命名约定: PLATFORMS key 的前缀匹配 Worker 名称即可
    platform_key = None
    name_lower = name.lower()
    
    for key in PLATFORMS:
        platform_prefix = key.split('_')[0]
        if platform_prefix in name_lower:
            platform_key = key
            break
    
    # 兜底防止出错
    if not platform_key:
        platform_key = next(iter(PLATFORMS.keys()))
    
    config = PLATFORMS[platform_key]
    MAX_RETRY = 2 # 总共尝试2次不同平台
    
    while True:
        # 从队列获取任务: (新闻ID, 已重试次数)
        news_id, retry_count = await queue.get()
        try:
            print(f"[{name}] 正在处理 ID: {news_id} (重试次数:{retry_count})...")
            
            # 1. 获取数据
            titles, contents, count = await get_grouped_news(db_conn, news_id)
            if count <= 0:
                print(f"[{name}] ID {news_id} 没有新闻数据，跳过")
                queue.task_done()
                continue

            # 2. 根据新闻数量选择不同Prompt
            if count == 1:
                # 单条新闻：保留原标题，提炼干净内容，提取地点和关键词
                prompt = f"""
                ### Role
                You are a professional News Editor. Your task is to standardize news into a global GIS format.

                ### Task
                1. Summarize the following news into a clean, fluent English passage (300-500 words).
                2. Extract exactly ONE specific core location name in English (e.g., "Cotai, Macau, China").
                3. Extract 3-5 keywords in English.

                ### CRITICAL: Language Requirement
                Regardless of the input language, the output JSON fields ("full_text", "location", "keywords") MUST be in ENGLISH.

                Input Title: {titles}
                Input Content: {contents}

                Return strictly in JSON format:
                {{
                    "full_text": "The summarized news in English",
                    "location": "The single location name in English",
                    "keywords": ["tag1", "tag2", "tag3"]
                }}
                """
            else:
                # 多条新闻聚合：提炼标题、摘要、地点、关键词
                prompt = f"""
                ### Role
                You are a senior News Synthesizer for a global news map.

                ### Task
                1. Merge all provided news into ONE single, coherent English report.
                2. Create a unified English Title.
                3. Write a deep-summary passage in English (300-500 words), merging all facts from sources.
                4. Extract exactly ONE specific core location name in English (e.g., "Cotai, Macau, China").
                5. Extract 3-5 keywords in English.

                ### CRITICAL: Language Requirement
                Regardless of the input language, the output JSON fields ("full_text", "location", "keywords") MUST be in ENGLISH.

                Source Titles: {titles}
                Source Contents: {contents}

                Return strictly in JSON format:
                {{
                    "title": "The synthesized English title",
                    "full_text": "The synthesized English summary",
                    "location": "The single central location in English",
                    "keywords": ["tag1", "tag2", "tag3"]
                }}
                """

            # 3. 调用 AI
            headers = {"Authorization": f"Bearer {config['key']}"}
            payload = {
                "model": config['model'],
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            
            # 合并平台专属扩展参数 支持任意厂商私有字段
            if "extra_options" in config:
                payload.update(config["extra_options"])
            
            response = await client.post(config['url'], headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            raw_content = response.json()["choices"][0]["message"]["content"]
            cleaned_content = clean_json_response(raw_content)
            ai_result = json.loads(cleaned_content)
            
            # 4. 获取坐标
            loc_name = ai_result.get("location", "")
            lat, lon = await get_coordinates(client, loc_name)
            
            # 5. 准备写入数据
            update_data = {
                "location": loc_name,
                "latitude": lat,
                "longitude": lon,
                "keywords": json.dumps(ai_result.get("keywords", []), ensure_ascii=False)
            }
            
            if count == 1:
                # 单条新闻：保留原始标题，使用AI清理后的内容
                update_data["title"] = titles
                update_data["full_text"] = ai_result.get("full_text", contents)
            else:
                # 多条新闻：AI生成全部字段
                update_data["title"] = ai_result.get("title", "")
                update_data["full_text"] = ai_result.get("full_text", "")
            
            # 6. 写入数据库
            await update_grouped_news(db_conn, news_id, update_data)
            
            print(f"✅ [{name}] 完成 ID {news_id}: {loc_name} ({lat}, {lon})")
            
        except Exception as e:
            if retry_count < MAX_RETRY:
                # 失败重新放回队列，下一次会被另一个平台Worker捡到
                await queue.put( (news_id, retry_count + 1) )
                print(f"⚠️  [{name}] ID {news_id} 失败，重新入队，下次重试")
            else:
                print(f"❌ [{name}] ID {news_id} 跨平台重试全部失败，永久放弃: {str(e)[:100]}")
        finally:
            # 告诉队列任务完成
            queue.task_done()

async def process_grouped_data(grouped_ids):
    queue = asyncio.Queue()
    
    # 1. 将所有任务塞进队列 (ID + 初始重试次数0)
    for news_id in grouped_ids:
        await queue.put( (news_id, 0) )

    # ✅ 全局单数据库连接 整个程序只打开一次
    # ✅ SQLite WAL模式性能提升50倍以上
    async with aiosqlite.connect(DB_PATH) as db_conn, httpx.AsyncClient() as client:
        # SQLite最佳性能配置
        await db_conn.execute("PRAGMA journal_mode = WAL")
        await db_conn.execute("PRAGMA synchronous = NORMAL")
        await db_conn.execute("PRAGMA cache_size = -20000")
        await db_conn.execute("PRAGMA temp_store = MEMORY")
        await db_conn.commit()

        # 2. 启动并发工人（Worker）
        workers = []

        ZHIPU_CONCURRENCY = 1
        SILICON_CONCURRENCY = 1

        # 启动智谱工人
        for i in range(ZHIPU_CONCURRENCY):
            workers.append(asyncio.create_task(worker(f"ZhiPu-{i}", queue, client, db_conn)))
            
        # 启动硅基工人
        for i in range(SILICON_CONCURRENCY):
            workers.append(asyncio.create_task(worker(f"Silicon-{i}", queue, client, db_conn)))

        # 3. 等待队列中所有任务被处理完
        await queue.join()

        # 4. 任务全部完成后，取消所有工人
        for w in workers:
            w.cancel()

if __name__ == "__main__":
    ids =[11]
    
    asyncio.run(process_grouped_data(ids))