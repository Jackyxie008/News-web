import asyncio
import os
import json
import random
import httpx
import aiosqlite
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

# 加载环境变量
load_dotenv()

DB_PATH = Path("backend/data/data.db")

# API 配置映射
PLATFORMS = {
    "zhi_pu": {
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "rate_limit": 0.5,
        "concurrency": 1,
        "key": os.getenv("GLM_API_KEY"),
        "model": "GLM-4.5-Flash",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    },
    "zhi_pu_cn": {
        "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "rate_limit": 0.5,
        "concurrency": 1,
        "key": os.getenv("GLM_CN_API_KEY"),
        "model": "GLM-4.7-Flash",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    },
    "silicon": {
        "url": "https://api.siliconflow.cn/v1/chat/completions",
        "rate_limit": 1.0,
        "concurrency": 1,
        "key": os.getenv("SILICONFLOW_API_KEY"),
        "model": "Qwen/Qwen3.5-4B",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    },
    "nim_minimax-m2.7": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "rate_limit": 0.1,
        "concurrency": 1,
        "key": os.getenv("NIM_API_KEY"),
        "model": "minimaxai/minimax-m2.7",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    },
    "nim_deepseek-v3.2": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "rate_limit": 0.1,
        "concurrency": 1,
        "key": os.getenv("NIM_API_KEY"),
        "model": "deepseek-ai/deepseek-v3.2",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    },
    "nim_step-3.5-flash": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "rate_limit": 0.1,
        "concurrency": 1,
        "key": os.getenv("NIM_API_KEY"),
        "model": "stepfun-ai/step-3.5-flash",
        "extra_options": {
        "thinking": {
            "type": "disabled"
            }
        }
    }
}

# 地图并发锁（依然保持 1，保护 IP）
map_semaphore = asyncio.Semaphore(1)

# 平台级限流状态
platform_last_request = defaultdict(float)

# 平台熔断状态
platform_fail_count = defaultdict(int)
platform_circuit_breaker = defaultdict(float)

# 全局停止事件 优雅退出用
stop_event = asyncio.Event()

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
    """地理编码：带多级降级搜索 自动向上查找行政区"""
    if not location: return None, None
    
    # 生成分级搜索列表 从细到粗
    search_levels = [location]
    
    # 按空格、逗号拆分地名 生成降级搜索项
    parts = [p.strip() for p in location.replace(',', ' ').split() if p.strip()]
    for i in range(len(parts)-1, 0, -1):
        search_levels.append(' '.join(parts[:i]))
    
    async with map_semaphore:
        for level, query in enumerate(search_levels):
            try:
                headers = {"User-Agent": "NewsMap/1.0"}
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": query, "format": "json", "limit": 1},
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
                    continue
                
                if resp.status_code != 200:
                    continue
                
                data = resp.json()
                if data:
                    if level > 0:
                        print(f"\033[93m⚠️  地名降级匹配: '{location}' → '{query}'\033[0m")
                    return data[0]["lat"], data[0]["lon"]
                
            except Exception as e:
                print(f"\033[93m⚠️ 地理编码请求异常: {str(e)[:60]}\033[0m")
                continue
    
    # 所有级别都搜索失败
    print(f"\033[91m❌ 地名匹配失败: {location}\033[0m")
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

async def worker(name, platform_key, queue, client, db_conn):
    """消费者工人：绑定指定平台"""
    config = PLATFORMS[platform_key]
    MAX_RETRY = 2 # 总共尝试2次不同平台
    
    while True:
        # 从队列获取任务: (新闻ID, 已重试次数)
        news_id, retry_count = await queue.get()
        try:
            if stop_event.is_set():
                queue.task_done()
                break
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
            current_time = asyncio.get_event_loop().time()
            
            # ✅ 平台级限流 + 随机抖动防封
            rate_limit = config.get("rate_limit", 1.0)
            min_interval = 1.0 / rate_limit
            jitter = random.uniform(-0.2, 0.2) * min_interval
            
            time_since_last = current_time - platform_last_request[platform_key]
            wait_time = max(0, min_interval + jitter - time_since_last)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # ✅ 熔断检查：平台已熔断时将任务放回队列由其他平台处理
            if platform_circuit_breaker[platform_key] > current_time:
                
                # ✅ 全局健康检查：检测是否所有平台都已经熔断
                all_dead = True
                for pf in PLATFORMS.keys():
                    if platform_circuit_breaker[pf] <= current_time:
                        all_dead = False
                        break
                
                if all_dead:
                    print("\n\033[91m🚨 所有API平台全部熔断！发起优雅停止\033[0m")
                    print("🚨 请检查你的API密钥是否被封禁，或者限流配置是否过高\n")
                    stop_event.set()
                    queue.task_done()
                    continue
                
                # ✅ 单任务回滚次数保护：防止同一个任务无限死循环
                if retry_count >= 5:
                    print(f"\033[91m❌ ID {news_id} 回滚次数超限 永久放弃\033[0m")
                    queue.task_done()
                    continue
                
                # 正常回滚到其他平台
                await queue.put( (news_id, retry_count + 1) )
                await asyncio.sleep(10)
                queue.task_done()
                continue
            
            platform_last_request[platform_key] = asyncio.get_event_loop().time()
            
            headers = {
                "Authorization": f"Bearer {config['key']}",
                "Content-Type": "application/json",
                "User-Agent": "NewsMapBot/1.0",
                **config.get("extra_headers", {})
            }
            payload = {
                "model": config['model'],
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1 + random.uniform(-0.03, 0.03)
            }
            
            # 合并平台专属扩展参数 支持任意厂商私有字段
            if "extra_options" in config:
                payload.update(config["extra_options"])
            
            try:
                response = await client.post(config['url'], headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                
                # 成功重置失败计数
                platform_fail_count[platform_key] = 0
                
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                
                if status == 400 or status == 403:
                    # ❗ 400/403 代表内容违规 安全策略拒绝 绝对不能重试
                    # 反复提交违规内容会导致整个账号被永久封禁
                    print(f"\033[91m🚫 ID {news_id} 内容违规被平台拒绝 永久放弃此任务 不会重试\033[0m")
                    platform_fail_count[platform_key] = 0
                    queue.task_done()
                    continue
                
                # 其他错误正常处理
                platform_fail_count[platform_key] += 1
                
                if status == 429:
                    # 触发限流 指数退避
                    backoff = 2 ** min(platform_fail_count[platform_key], 5)
                    print(f"\033[93m⚠️  平台 {platform_key} 限流 等待 {backoff} 秒\033[0m")
                    await asyncio.sleep(backoff)
                
                if platform_fail_count[platform_key] >= 10:
                    # 连续失败10次 熔断15分钟
                    platform_circuit_breaker[platform_key] = current_time + 900
                    print(f"\033[91m🚨 平台 {platform_key} 连续失败10次 熔断15分钟\033[0m")
                
                raise
            
            raw_content = response.json()["choices"][0]["message"]["content"]
            cleaned_content = clean_json_response(raw_content)
            ai_result = json.loads(cleaned_content)
            
            # 4. 获取坐标
            loc_name = ai_result.get("location", "")
            lat, lon = await get_coordinates(client, loc_name)
            
            # 5. 准备写入数据 严格类型校验
            update_data = {}
            
            # 地点名称 截断防止超长
            update_data["location"] = str(loc_name).strip()[:200] if loc_name else ""
            
            # 经纬度严格范围校验
            try:
                update_data["latitude"] = float(lat) if lat and -90 <= float(lat) <= 90 else None
            except (ValueError, TypeError):
                update_data["latitude"] = None
                
            try:
                update_data["longitude"] = float(lon) if lon and -180 <= float(lon) <= 180 else None
            except (ValueError, TypeError):
                update_data["longitude"] = None
            
            # 关键词 保证永远返回安全JSON
            update_data["keywords"] = json.dumps(ai_result.get("keywords", []), ensure_ascii=False)
            
            # 标题和正文
            if count == 1:
                # 单条新闻：保留原始标题，使用AI清理后的内容
                update_data["title"] = str(titles).strip()[:500] if titles else ""
                update_data["full_text"] = str(ai_result.get("full_text", contents)).strip() if contents else ""
            else:
                # 多条新闻：AI生成全部字段
                update_data["title"] = str(ai_result.get("title", "")).strip()[:500]
                update_data["full_text"] = str(ai_result.get("full_text", "")).strip()
            
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

        # 2. 自动启动所有平台Worker
        workers = []

        for platform_key, config in PLATFORMS.items():
            concurrency = config.get("concurrency", 1)
            for i in range(concurrency):
                worker_name = f"{platform_key}-{i}"
                workers.append(asyncio.create_task(worker(worker_name, platform_key, queue, client, db_conn)))
        
        print(f"✅ 已启动 {len(workers)} 个工作线程，共 {len(PLATFORMS)} 个平台")

        # 3. 等待队列中所有任务被处理完
        await queue.join()

        # 4. 任务全部完成后，取消所有工人
        for w in workers:
            w.cancel()

if __name__ == "__main__":
    ids =[12, 13, 14, 15, 16]
    
    asyncio.run(process_grouped_data(ids))