import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("backend/data/data.db")

CATEGORY_MAP_ZH = {
    "politics": "政治",
    "finance": "经济",
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
    "finance": "Finance",
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
    parts = [part.strip() for part in location.split(",") if part.strip()]
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
    lat = row["latitude"]
    lng = row["longitude"]
    if lat is None or lng is None:
        return None

    try:
        lat_value = float(lat)
        lng_value = float(lng)
    except (TypeError, ValueError):
        return None

    if not (-90 <= lat_value <= 90 and -180 <= lng_value <= 180):
        return None

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
    source_list = parse_sources(row["all_sources"] or "")
    default_source = row["media"] or ("Unknown Source" if lang == "en" else "未知来源")
    link_items: list[dict[str, str]] = []
    for idx, url in enumerate(links):
        source = source_list[idx] if idx < len(source_list) and source_list[idx] else default_source
        link_items.append({"url": url, "source": source})

    image_candidates = parse_links(row["image_url"] or "")
    image_url = image_candidates[0] if image_candidates else ""
    image_source = (row["image_source"] or "").strip() or (source_list[0] if source_list else default_source)

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
        "location": location or country,
        "published": row["published"] or "",
        "newsType": category_map.get(category, "Unknown" if lang == "en" else "文化"),
        "keywords": keywords,
        "fullText": full_text,
        "links": links,
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
              g.image_source,
              g.all_sources,
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
              g.image_source,
              g.all_sources,
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
