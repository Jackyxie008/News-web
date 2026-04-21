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

# API 配置映射 - 从外部JSON配置文件加载
PLATFORMS = {}

try:
    with open(Path("backend/data/platforms.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 自动注入环境变量中的API密钥
    enabled_count = 0
    for platform_id, platform_config in config.items():
        # 只加载启用的平台
        if not platform_config.get("enabled", False):
            continue
            
        env_key = platform_config.pop("env_key")
        platform_config["key"] = os.getenv(env_key)
        PLATFORMS[platform_id] = platform_config
        enabled_count += 1
        
    print(f"✅ 已加载 {enabled_count} 个启用的API平台，共定义 {len(config)} 个平台")
    
except Exception as e:
    print(f"\033[91m❌ 加载平台配置文件失败: {str(e)}\033[0m")
    print("请检查 backend/data/platforms.json 文件是否存在并且格式正确")
    exit(1)

# 地图并发锁（依然保持 1，保护 IP）
map_semaphore = asyncio.Semaphore(1)

# 平台级限流状态
platform_last_request = defaultdict(float)

# 平台熔断状态
platform_fail_count = defaultdict(int)
platform_circuit_breaker = defaultdict(float)

# 任务-平台失败追踪：{ news_id: { platform_key: failed_timestamp, ... } }
news_platform_failures = defaultdict(dict)

# 失败回避冷却时间（秒）：同一个平台处理同一条新闻失败后，至少过这么久才能再碰这条新闻
FAILURE_COOLDOWN = 120

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
    # 1. 先查询added字段(新增ID)，如果存在则优先用added，否则用全部news_id
    cursor = await conn.execute(
        "SELECT added, news_id FROM grouped_news WHERE id = ?",
        (id,)
    )
    row = await cursor.fetchone()
    
    if not row:
        return "", "", 0
    
    added_str, all_news_ids_str = row
    
    # 只有added有值时才处理（说明有新增内容）
    # 如果added为空说明该分组已经处理完成，不再重复处理
    if added_str and added_str.strip():
        news_ids_str = added_str
    else:
        return "", "", 0
    
    news_ids = [int(nid.strip()) for nid in news_ids_str.split(',') if nid.strip().isdigit()]
    
    if not news_ids:
        return "", "", 0
    
    # 2. 按authority从高到低排序
    LIMIT_COUNT = 2
    placeholders = ','.join(['?'] * len(news_ids))
    query = f"""
        SELECT title, full_text 
        FROM news 
        WHERE id IN ({placeholders}) 
        ORDER BY authority DESC
        LIMIT {LIMIT_COUNT}
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

def generate_search_levels(location):
    """生成单个地名的降级搜索队列"""
    if not location: return []
    
    search_levels = []
    
    # 第一优先级：逗号分层降级
    comma_parts = [p.strip() for p in location.split(',') if p.strip()]
    for i in range(len(comma_parts)):
        search_levels.append(', '.join(comma_parts[i:]))
    
    # 第二优先级：空格降级
    space_parts = [p.strip() for p in location.replace(',', ' ').split() if p.strip()]
    if len(space_parts) >= 2:
        for i in range(1, len(space_parts)-1):
            search_levels.append(' '.join(space_parts[i:]))
    
    # 去重保持顺序
    seen = set()
    return [x for x in search_levels if not (x in seen or seen.add(x))]


async def get_coordinates(client, location_en, location_cn=None):
    """地理编码：双语交叉搜索 同级先英后中 命中即返回"""
    if not location_en and not location_cn:
        return None, None
    
    # 生成各自降级队列
    en_levels = generate_search_levels(location_en)
    cn_levels = generate_search_levels(location_cn) if location_cn else []
    
    # ✅ 交叉合并：同一级别先试英文，再试中文
    search_queue = []
    max_levels = max(len(en_levels), len(cn_levels))
    
    for level in range(max_levels):
        if level < len(en_levels):
            search_queue.append( ("en", en_levels[level], level) )
        if level < len(cn_levels) and cn_levels[level] != en_levels[level]:
            search_queue.append( ("cn", cn_levels[level], level) )
    
    async with map_semaphore:
        for lang, query, level in search_queue:
            try:
                headers = {"User-Agent": "NewsMap/1.0"}
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "accept-language": lang
                    },
                    headers=headers,
                    timeout=15
                )
                await asyncio.sleep(1.1)
                
                if resp.status_code == 403:
                    print("\n\033[91m🚨 OpenStreetMap API 403 IP已被临时封禁\033[0m")
                    return None, None
                
                if resp.status_code == 429:
                    print("\033[93m⚠️ OSM 请求频率超限 等待5秒\033[0m")
                    await asyncio.sleep(5)
                    continue
                
                if resp.status_code != 200:
                    continue
                
                data = resp.json()
                if data:
                    if level > 0:
                        print(f"\033[93m⚠️  {lang.upper()} 降级匹配: '{query}' 第{level}级\033[0m")
                    return data[0]["lat"], data[0]["lon"]
                
            except Exception as e:
                print(f"\033[93m⚠️ 地理编码异常: {str(e)[:60]}\033[0m")
                continue
    
    print(f"\033[91m❌ 地名匹配失败: {location_en}\033[0m")
    return None, None

async def get_all_unprocessed_ids(conn):
    """获取数据库中所有未处理的分组ID"""
    cursor = await conn.execute(
        "SELECT id FROM grouped_news WHERE latitude IS NULL OR latitude = '' ORDER BY id ASC"
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]

async def get_all_added_ids(conn):
    """获取数据库中所有有新增新闻的分组ID"""
    cursor = await conn.execute(
        "SELECT id FROM grouped_news WHERE added != '' ORDER BY id ASC"
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
        # 从队列获取任务: (新闻ID, 已重试次数, 跳过平台集合)
        task = await queue.get()
        if len(task) == 2:
            # 兼容旧格式任务
            news_id, retry_count = task
            skip_platforms = set()
        else:
            news_id, retry_count, skip_platforms = task
            
        try:
            if stop_event.is_set():
                break

            # ✅ 前置检查：这个新闻在当前平台是否还在冷却回避期
            current_time = asyncio.get_event_loop().time()
            failed_time = news_platform_failures.get(news_id, {}).get(platform_key, 0)
            
            # 如果这个平台还在回避冷却期，或者明确要求跳过
            if current_time < failed_time or platform_key in skip_platforms:
                # 把任务放回队列末尾，给其他平台机会
                await queue.put( (news_id, retry_count, skip_platforms) )
                # 短暂延迟避免死循环抢任务
                await asyncio.sleep(0.1)
                continue
            
            print(f"[{name}] 正在处理 ID: {news_id} (重试次数:{retry_count})...")
            
            # 1. 获取数据
            titles, contents, count = await get_grouped_news(db_conn, news_id)
            if count <= 0:
                print(f"[{name}] ID {news_id} 没有新闻数据，跳过")
                continue

            # 统一使用高级提示词模板，无论新闻数量多少
            prompt = """
            ### Role
            You are a professional News Editor and GIS Data Specialist. Your task is to standardize news into a global GIS format.

            ### Task
            1. Summarize the following news into a clean, fluent passage (300-500 words).
            2. Create professional titles in both English and Chinese.
            3. **Location Extraction (CRITICAL: Core Event Location ONLY)**:
            - **DEFINITION of "Core Event Location"**: Extract the specific location(s) where the **main action/event** of the news physically takes place or is centered on. DO NOT extract locations that are only mentioned as background, origin, headquarters, historical context, or future destinations.
            - **Granularity Priority**: Always try to find the most specific location in this order: Landmark -> City -> Province -> Country.
            - **Adaptive Precision Rule**:
                - If a specific level (1-3) is mentioned as the **core event location**, return "[Specific], [Country]".
                - If ONLY a broad level (4) is mentioned as the **core event location** (e.g., national policy, macro economy), return ONLY the **[Country Name]**.
                - DO NOT force-fill or hallucinate a city.
                - **IF NO EXACT CORE EVENT LOCATION IS MENTIONED OR INFERABLE**: return **empty string ""** for both fields. DO NOT invent a location.
            - **Independent Geo-Entities**: For international waters, straits, or cross-border areas (e.g., "Strait of Hormuz", "Gaza Strip"), return the entity name ALONE. Do NOT append a country.
            - **Anti-Redundancy & Alias Ban**:
                - NO repeating names (e.g., NO "London, UK, UK").
                - NO aliases (e.g., NO "USA, United States"). Use only the formal short name.
                - If City equals Country (e.g., Singapore), return only the name ONCE.
                - Administrative regions (e.g., Hong Kong, Macau) should be "City, Country" (e.g., "Hong Kong, China").
            - **NON-LOCATION Exclusion (STRICT)**: A location is the place where the event occurs. DO NOT extract any of the following as a core event location:
                - Object's nationality or birthplace (e.g., "French President" does NOT make France a core location, "Japan's team" does NOT make Japan a core location)
                - Historical or background locations (e.g., "discovered in 2020 in London" for a 2024 event in Paris)
                - Destination of a future plan (e.g., "will travel to Tokyo next week" - Tokyo is NOT a core location for today's news)
            - **Multi-Location Handling**:
                - If the news involves **multiple distinct core locations** (e.g., talks between two cities, disasters in several regions), output **all central locations**.
                - Separate locations with **semicolon + space (`;`)**.
                - Each location must individually pass the "Core Event Location" test.
                - DO NOT output a location list — use `;` as the only delimiter.
            4. Extract 3-6 keywords.
            5. Classify into ONE category: [politics, military, disaster, security, finance, diplomacy, society, tech, energy, environment, sports, entertainment].

            ### Language Requirement
            - Input may be Chinese or English.
            - Output MUST be high-quality, native-style content in BOTH languages.
            - Do NOT use machine translation; write each version independently.

            ### Examples of Core Event Location Extraction (for reference)

            **Example 1 (Correct - Single Core Location)**
            News: "The trade deal was signed in Shanghai today. The Chinese Ministry of Commerce in Beijing announced the details."
            - Correct location_en: "Shanghai, China" (Event signing location)
            - Wrong location_en: "Shanghai, China; Beijing, China" (Beijing is only the announcement origin, not the core event)

            **Example 2 (Correct - Empty for No Core Location)**
            News: "Apple's CEO Tim Cook, a native of Alabama, discussed future plans for the company's Cupertino campus."
            - Correct location_en: "" (No physical event location mentioned)
            - Wrong location_en: "Alabama, USA" or "Cupertino, USA" (These are background/headquarters, not event locations)

            **Example 3 (Correct - Multiple Core Locations)**
            News: "Protests erupted simultaneously in Paris and Lyon."
            - Correct location_en: "Paris, France; Lyon, France"
            - Wrong location_en: "France" (Too broad, misses specific cities)

            Source Title: """ + titles + """
            Source Content: """ + contents + """

            ### Output Format (STRICT JSON)
            Return ONLY a raw JSON object. No markdown code blocks, no preamble.
            {
                "title_en": "Professional English title",
                "title_cn": "专业中文标题",
                "full_text_en": "Professional English summary",
                "full_text_cn": "专业中文摘要",
                "location_en": "Specific, General (or 'Paris, France; Berlin, Germany' for multiple, or '' for none)",
                "location_cn": "具体, 总体 (或 '巴黎, 法国; 柏林, 德国' 表示多个, 或 '' 表示无)",
                "location_num": integer,
                "keywords_en": ["tag1", "tag2"],
                "keywords_cn": ["标签1", "标签2"],
                "category": "category_name"
            }
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
                    continue
                
                # ✅ 单任务回滚次数保护：防止同一个任务无限死循环
                if retry_count >= 3:
                    print(f"\033[91m❌ ID {news_id} 回滚次数超限 永久放弃\033[0m")
                    continue
                
                # 正常回滚到其他平台
                await queue.put( (news_id, retry_count + 1) )
                await asyncio.sleep(10)
                continue
            
            platform_last_request[platform_key] = asyncio.get_event_loop().time()
            
            headers = {
                "Authorization": f"Bearer {config['key']}",
                "Content-Type": "application/json",
                "User-Agent": "NewsMap/1.0",
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
                response = await client.post(config['url'], headers=headers, json=payload, timeout=240)
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
            
            # 解析AI结果，兼容不同平台的返回格式差异
            result = response.json()
            if "choices" in result and result["choices"]:
                raw_content = result["choices"][0]["message"]["content"]
            else:
                raw_content = result["message"]["content"]
            
            cleaned_content = clean_json_response(raw_content)
            ai_result = json.loads(cleaned_content)
            
            # 4. 获取坐标 双语交叉搜索 支持多地点 分号分隔格式 [地点1;地点2]
            loc_name_en = ai_result.get("location_en", "")
            loc_name_cn = ai_result.get("location_cn", "")
            
            if not loc_name_en.strip() and not loc_name_cn.strip():
                lat, lon = None, None
            else:
                # ✅ 支持多地点处理: 分号分隔的地点列表
                locations_en = [loc.strip() for loc in loc_name_en.split(';') if loc.strip()]
                locations_cn = [loc.strip() for loc in loc_name_cn.split(';') if loc.strip()]
                
                lat_list = []
                lon_list = []
                
                # 逐个处理每个地点
                max_locations = max(len(locations_en), len(locations_cn))
                
                for i in range(max_locations):
                    en = locations_en[i] if i < len(locations_en) else ""
                    cn = locations_cn[i] if i < len(locations_cn) else ""
                    
                    if not en.strip() and not cn.strip():
                        lat_list.append("")
                        lon_list.append("")
                        continue
                        
                    lat, lon = await get_coordinates(client, en, cn)
                    
                    lat_str = str(lat) if lat is not None else ""
                    lon_str = str(lon) if lon is not None else ""
                    
                    lat_list.append(lat_str)
                    lon_list.append(lon_str)
                
                # 用分号连接多个坐标 保持和地点一一对应
                lat = ';'.join(lat_list) if lat_list else None
                lon = ';'.join(lon_list) if lon_list else None
            
            # 5. 准备写入数据 严格类型校验
            update_data = {}
            
            # 双语地点名称 截断防止超长
            update_data["location_en"] = str(loc_name_en).strip()[:200] if loc_name_en else ""
            update_data["location_cn"] = str(loc_name_cn).strip()[:200] if loc_name_cn else ""
            
            
            # 经纬度存储 支持分号分隔的多坐标格式
            update_data["latitude"] = lat
            update_data["longitude"] = lon
            
            # 新闻类型
            category = ai_result.get("category", "").strip().lower()
            update_data["category"] = category
            
            # 关键词 中英文分别存储
            update_data["keywords_en"] = json.dumps(ai_result.get("keywords_en", []), ensure_ascii=False)
            update_data["keywords_cn"] = json.dumps(ai_result.get("keywords_cn", []), ensure_ascii=False)
            
            # 双语标题和正文
            update_data["title_en"] = str(ai_result.get("title_en", "")).strip()[:500]
            update_data["title_cn"] = str(ai_result.get("title_cn", "")).strip()[:500]
            update_data["full_text_en"] = str(ai_result.get("full_text_en", "")).strip()
            update_data["full_text_cn"] = str(ai_result.get("full_text_cn", "")).strip()
            
            
            # 6. 写入数据库
            update_data["added"] = ""
            await update_grouped_news(db_conn, news_id, update_data)
            
            print(f"✅ [{name}] 完成 ID {news_id}: {loc_name_en} ({lat}, {lon})")
            
            # ✅ 处理成功，清理这条新闻的失败记录释放内存
            news_platform_failures.pop(news_id, None)
        except Exception as e:
            # ✅ 详细错误日志：打印完整异常信息
            # error_type = type(e).__name__
            # error_msg = str(e)[:200]
            # error_trace = traceback.format_exc()
            # print(f"\n\033[91m❌ [{name}] ID {news_id} 处理失败详情:\033[0m")
            # print(f"   错误类型: {error_type}")
            # print(f"   错误信息: {error_msg}")
            # print(f"   堆栈跟踪:\n{error_trace[:500]}")
            
            # ✅ 记录这个平台处理这条新闻失败了
            current_time = asyncio.get_event_loop().time()
            news_platform_failures[news_id][platform_key] = current_time + FAILURE_COOLDOWN
            
            # ✅ 把当前平台加入跳过列表
            new_skip = set(skip_platforms)
            new_skip.add(platform_key)
            
            # 检查是否所有平台都已经试过了
            all_tried = len(new_skip) >= len(PLATFORMS)
            
            if all_tried:
                # 所有平台都试过一轮了，重置跳过列表，重试次数+1
                if retry_count < MAX_RETRY:
                    await queue.put( (news_id, retry_count + 1, set()) )
                    print(f"\033[93m⚠️  [{name}] ID {news_id} 所有平台都试过一轮，进入第 {retry_count+2} 轮重试\033[0m")
                else:
                    print(f"\033[91m❌ [{name}] ID {news_id} 跨平台重试全部失败，永久放弃\033[0m")
                    # 清理失败记录释放内存
                    news_platform_failures.pop(news_id, None)
            else:
                # 还有平台没试过，带着跳过列表重新入队
                await queue.put( (news_id, retry_count, new_skip) )
                print(f"\033[93m⚠️  [{name}] ID {news_id} 在 {platform_key} 失败，跳过此平台，交给其他平台处理\033[0m")
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

async def process_all_unprocessed():
    """自动获取并处理所有未处理的分组 主入口"""
    # ✅ 先单独查询待处理ID，然后关闭连接
    # ❌ 绝对不能在持有数据库连接的情况下调用process_grouped_data
    # 否则会导致双连接死锁，程序永远无法退出
    ids = []
    
    async with aiosqlite.connect(DB_PATH) as conn:
        ids = await get_all_unprocessed_ids(conn)
    
    if ids:
        print(f"发现 {len(ids)} 个未处理的新闻分组，开始处理...")
        await process_grouped_data(ids)
        print("\n✅ 所有分组数据处理完成！程序正常退出。")
    else:
        print("✅ 没有需要处理的新分组")

async def process_all_added():
    """自动获取并处理所有有新增新闻的分组 主入口"""
    ids = []
    
    async with aiosqlite.connect(DB_PATH) as conn:
        ids = await get_all_added_ids(conn)
    
    if ids:
        print(f"发现 {len(ids)} 个有新增新闻的分组，开始处理...")
        await process_grouped_data(ids)
        print("\n✅ 所有新增分组数据处理完成！程序正常退出。")
    else:
        print("✅ 没有需要处理的新增新闻分组")

if __name__ == "__main__":
    asyncio.run(process_all_added())
    # asyncio.run(process_all_added())
    # ids = [2]
    # ids = [i for i in range(1, 78)]
    # asyncio.run(process_grouped_data(ids))
