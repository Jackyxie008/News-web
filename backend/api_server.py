import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from pathlib import Path
from typing import Any

# 获取当前脚本所在文件夹的绝对路径 (即 backend 目录)
BASE_DIR = Path(__file__).resolve().parent

# 无论从哪启动，都以 backend 文件夹为起点
# 如果你的 data 文件夹在 backend/data/ 下：
DB_PATH = BASE_DIR / "data" / "data.db"

# 调试用：启动时打印一下，看路径对不对
print(f"正在连接数据库: {DB_PATH}")

CATEGORY_MAP_ZH = {
    "politics": "政治",
    "diplomacy": "外交",
    "security": "安全",
    "finance": "经济",
    "energy": "能源",
    "environment": "环境",
    "tech": "科技",
    "sports": "体育",
    "society": "社会",
    "military": "军事",
    "entertainment": "娱乐/文化",
    "international": "国际",
    "disaster": "灾害",
}

CATEGORY_MAP_EN = {
    "politics": "Politics",
    "diplomacy": "Diplomacy",
    "security": "Security",
    "finance": "Finance",
    "energy": "Energy",
    "environment": "Environment",
    "tech": "Tech",
    "sports": "Sports",
    "society": "Society",
    "military": "Military",
    "entertainment": "Entertainment/Culture",
    "international": "International",
    "disaster": "Disaster",
}


def normalize_lang(value: str | None) -> str:
    if value and value.strip().lower() == "en":
        return "en"
    return "zh"


def parse_ts(published: str) -> int:
    if not published:
        return 0
    text = published.strip().replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(text).timestamp() * 1000)
    except ValueError:
        return 0


def normalize_date(published: str) -> str:
    if not published:
        return ""
    text = published.strip()
    if len(text) >= 10:
        return text[:10]
    return text


def extract_country(location: str, lang: str) -> str:
    unknown = "Unknown" if lang == "en" else "未知地区"
    if not location:
        return unknown
    primary_location = next(
        (part.strip() for part in re.split(r"[;\n]+", location) if part.strip()),
        "",
    )
    if not primary_location:
        return unknown
    parts = [part.strip() for part in primary_location.split(",") if part.strip()]
    if not parts:
        return unknown
    return parts[-1]


def summary_text(full_text: str) -> str:
    if not full_text:
        return ""
    text = full_text.strip()
    if len(text) <= 120:
        return text
    return text[:120] + "..."


def calc_heat(news_ids_text: str) -> int:
    if not news_ids_text:
        return 40
    ids = [x.strip() for x in news_ids_text.split(",") if x.strip().isdigit()]
    return min(100, 40 + len(ids) * 8)


def parse_keywords(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()][:10]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in text.split(",") if item.strip()][:10]


def parse_links(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()][:20]
    except json.JSONDecodeError:
        pass
    links = [item.strip() for item in re.split(r"[,|;\n]+", text) if item.strip()]
    return links[:10]

def parse_tokens(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in re.split(r"[,|;\n，；]+", text) if item.strip()]

def parse_sources(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()][:20]
        if isinstance(data, dict):
            values = [str(v).strip() for _, v in sorted(data.items(), key=lambda x: str(x[0]))]
            return [v for v in values if v][:20]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in re.split(r"[,|;\n]+", text) if item.strip()][:20]


def is_url(text: str) -> bool:
    t = (text or "").strip().lower()
    return t.startswith("http://") or t.startswith("https://")


def parse_link_items(raw_links: str, default_source: str) -> list[dict[str, str]]:
    tokens = parse_tokens(raw_links)
    if not tokens:
        return []

    items: list[dict[str, str]] = []

    # 新格式: [来源, 链接, 来源, 链接, ...]
    paired = len(tokens) >= 2 and any(is_url(tokens[i]) for i in range(1, len(tokens), 2))
    if paired:
        i = 0
        while i + 1 < len(tokens):
            source = tokens[i].strip() or default_source
            url = tokens[i + 1].strip()
            if is_url(url):
                items.append({"url": url, "source": source})
            i += 2
        if items:
            return items[:10]

    # 兼容旧格式: 仅链接列表
    for token in tokens:
        if is_url(token):
            items.append({"url": token, "source": default_source})
    return items[:10]


def parse_image_info(raw_image: str, default_source: str) -> tuple[str, str]:
    tokens = parse_tokens(raw_image)
    if not tokens:
        return "", ""

    # 新格式: [图片来源, 图片链接]
    if len(tokens) >= 2 and is_url(tokens[1]):
        return tokens[1], (tokens[0].strip() or default_source)

    # 兼容: 只有图片链接
    if is_url(tokens[0]):
        return tokens[0], default_source

    return "", ""


def parse_coordinate_values(raw: Any) -> list[float]:
    if raw is None:
        return []
    if isinstance(raw, (int, float)):
        try:
            return [float(raw)]
        except (TypeError, ValueError):
            return []

    text = str(raw).strip()
    if not text:
        return []

    try:
        data = json.loads(text)
        if isinstance(data, list):
            values: list[float] = []
            for item in data:
                try:
                    values.append(float(item))
                except (TypeError, ValueError):
                    continue
            return values
    except json.JSONDecodeError:
        pass

    tokens = [item.strip() for item in re.split(r"[;,\n，；|]+", text) if item.strip()]
    values: list[float] = []
    for token in tokens:
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


def normalize_coords(lat: float, lng: float) -> tuple[float, float] | None:
    lat_ok = -90 <= lat <= 90
    lng_ok = -180 <= lng <= 180
    if lat_ok and lng_ok:
        return lat, lng

    # 部分数据可能经纬度写反：尝试自动纠偏
    swapped_lat_ok = -90 <= lng <= 90
    swapped_lng_ok = -180 <= lat <= 180
    if swapped_lat_ok and swapped_lng_ok:
        return lng, lat
    return None


def parse_locations(raw_location: str) -> list[str]:
    if not raw_location:
        return []
    return [part.strip() for part in re.split(r"[;\n]+", raw_location) if part.strip()]


def parse_location_points(row: sqlite3.Row, lang: str) -> list[dict[str, Any]]:
    lat_values = parse_coordinate_values(row["latitude"])
    lng_values = parse_coordinate_values(row["longitude"])
    if not lat_values or not lng_values:
        return []

    location_raw = (
        row["location_en"] if lang == "en" else row["location_cn"]
    ) or (
        row["location_cn"] if lang == "en" else row["location_en"]
    ) or ""
    names = parse_locations(location_raw)

    points: list[dict[str, Any]] = []
    pair_count = min(len(lat_values), len(lng_values))
    for i in range(pair_count):
        normalized = normalize_coords(lat_values[i], lng_values[i])
        if not normalized:
            continue
        lat, lng = normalized
        item: dict[str, Any] = {"lat": lat, "lng": lng}
        if i < len(names):
            item["name"] = names[i]
        points.append(item)
    return points

def extract_keywords_fallback(title: str, full_text: str) -> list[str]:
    text = f"{title} {full_text}".strip()
    if not text:
        return []
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text)
    dedup: list[str] = []
    seen = set()
    for word in words:
        w = word.strip()
        lw = w.lower()
        if lw in seen:
            continue
        seen.add(lw)
        dedup.append(w)
        if len(dedup) >= 5:
            break
    return dedup


def row_to_news(row: sqlite3.Row, lang: str) -> dict[str, Any] | None:
    points = parse_location_points(row, lang)
    if not points:
        return None
    lat_value = points[0]["lat"]
    lng_value = points[0]["lng"]

    category = (row["category"] or "").strip().lower()
    title = (
        row["title_en"] if lang == "en" else row["title_cn"]
    ) or (
        row["title_cn"] if lang == "en" else row["title_en"]
    ) or row["primary_title"] or (
        f"News #{row['id']}" if lang == "en" else f"新闻 #{row['id']}"
    )
    full_text = (
        row["full_text_en"] if lang == "en" else row["full_text_cn"]
    ) or (
        row["full_text_cn"] if lang == "en" else row["full_text_en"]
    ) or row["primary_full_text"] or ""
    location = (
        row["location_en"] if lang == "en" else row["location_cn"]
    ) or (
        row["location_cn"] if lang == "en" else row["location_en"]
    ) or ""
    country = extract_country(location, lang)
    # 根据语言选择对应的关键词字段
    keywords_field = "keywords_en" if lang == "en" else "keywords_cn"
    keywords = parse_keywords(row[keywords_field] or "")
    if not keywords:
        keywords = extract_keywords_fallback(title, full_text)
    links = parse_links(row["links"] or "")
    if not links and row["primary_link"]:
        links = [str(row["primary_link"]).strip()]
    default_source = row["media"] or ("Unknown Source" if lang == "en" else "未知来源")
    link_items = parse_link_items(row["links"] or "", default_source)
    if not link_items and links:
        link_items = [{"url": url, "source": default_source} for url in links]

    image_url, image_source = parse_image_info(row["image_url"] or "", default_source)

    category_map = CATEGORY_MAP_EN if lang == "en" else CATEGORY_MAP_ZH

    return {
        "id": str(row["id"]),
        "title": title,
        "summary": summary_text(full_text),
        "date": normalize_date(row["published"] or ""),
        "ts": parse_ts(row["published"] or ""),
        "media": row["media"] or ("Unknown Media" if lang == "en" else "未知媒体"),
        "continent": "Unknown" if lang == "en" else "未知洲",
        "country": country,
        "type": category_map.get(category, "Unknown" if lang == "en" else "文化"),
        "heat": calc_heat(row["news_id"] or ""),
        "lat": lat_value,
        "lng": lng_value,
        "locations": points,
        "location": location or country,
        "published": row["published"] or "",
        "newsType": category_map.get(category, "Unknown" if lang == "en" else "文化"),
        "keywords": keywords,
        "fullText": full_text,
        "links": [item["url"] for item in link_items] if link_items else links,
        "linkItems": link_items,
        "imageUrl": image_url,
        "imageSource": image_source,
    }


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    # 启用WAL日志模式，允许读写并发不阻塞
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA mmap_size = 268435456")
    return conn


def fetch_news_list(limit: int = 1000, lang: str = "zh") -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
              g.id,
              g.news_id,
              g.title_en,
              g.title_cn,
              g.full_text_en,
              g.full_text_cn,
              g.published,
              g.location_en,
              g.location_cn,
              g.latitude,
              g.longitude,
              g.category,
              g.keywords_en,
              g.keywords_cn,
              g.links,
              g.image_url,
              (
                SELECT n.source
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS media,
              (
                SELECT n.title
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS primary_title,
              (
                SELECT n.full_text
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS primary_full_text,
              (
                SELECT n.link
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS primary_link
            FROM grouped_news g
            ORDER BY COALESCE(g.published, '') DESC, g.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_news(row, lang)
        if item is not None:
            result.append(item)
    return result


def fetch_news_detail(news_id: str, lang: str = "zh") -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
              g.id,
              g.news_id,
              g.title_en,
              g.title_cn,
              g.full_text_en,
              g.full_text_cn,
              g.published,
              g.location_en,
              g.location_cn,
              g.latitude,
              g.longitude,
              g.category,
              g.keywords_en,
              g.keywords_cn,
              g.links,
              g.image_url,
              (
                SELECT n.source
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS media,
              (
                SELECT n.title
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS primary_title,
              (
                SELECT n.full_text
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS primary_full_text,
              (
                SELECT n.link
                FROM news n
                WHERE instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
                ORDER BY n.authority DESC
                LIMIT 1
              ) AS primary_link
            FROM grouped_news g
            WHERE g.id = ?
            LIMIT 1
            """,
            (news_id,),
        ).fetchone()

    if row is None:
        return None
    return row_to_news(row, lang)


class ApiHandler(BaseHTTPRequestHandler):
    def _set_common_headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self._set_common_headers(status)
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self) -> None:
        self._set_common_headers(200)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if not DB_PATH.exists():
            self._write_json({"error": f"数据库不存在: {DB_PATH.as_posix()}"}, status=500)
            return

        if path == "/api/news":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", ["1000"])[0])
            except ValueError:
                limit = 1000
            lang = normalize_lang(query.get("lang", ["zh"])[0])
            items = fetch_news_list(limit=max(1, min(limit, 5000)), lang=lang)
            self._write_json({"items": items})
            return

        if path.startswith("/api/news/"):
            news_id = path.removeprefix("/api/news/").strip()
            if not news_id:
                self._write_json({"error": "参数错误"}, status=400)
                return
            query = parse_qs(parsed.query)
            lang = normalize_lang(query.get("lang", ["zh"])[0])
            item = fetch_news_detail(news_id, lang=lang)
            if item is None:
                self._write_json({"error": "未找到该新闻"}, status=404)
                return
            self._write_json(item)
            return

        self._write_json({"error": "Not Found"}, status=404)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), ApiHandler)
    print("API 服务已启动: http://127.0.0.1:8000")
    server.serve_forever()
