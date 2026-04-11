import aiosqlite
from pathlib import Path

async def get_grouped_news(id):
    """
    根据分组ID获取聚合新闻
    参数:
        id: grouped_news表中的分组ID
    返回:
        (titles_text, contents_text): 合并后的标题字符串和正文字符串
    """
    db_path = Path("backend/data/data.db")
    
    async with aiosqlite.connect(db_path) as conn:
        # 1. 查询分组对应的新闻ID列表
        cursor = await conn.execute(
            "SELECT news_id FROM grouped_news WHERE id = ?",
            (id,)
        )
        row = await cursor.fetchone()
        
        if not row or not row[0]:
            return "", ""
        
        news_ids_str = row[0]
        news_ids = [int(nid.strip()) for nid in news_ids_str.split(',') if nid.strip().isdigit()]
        
        if not news_ids:
            return "", ""
        
        # 2. 按authority从高到低排序，取前5条新闻
        placeholders = ','.join(['?'] * len(news_ids))
        query = f"""
            SELECT title, full_text 
            FROM news 
            WHERE id IN ({placeholders}) 
            ORDER BY authority DESC 
            LIMIT 2
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
                # 每条正文只取前3000个字符
                cleaned_text = full_text.strip()
                if len(cleaned_text) > 3000:
                    cleaned_text = cleaned_text[:3000] + "..."
                contents.append(cleaned_text)
        
        titles_text = '\n\n'.join(titles)
        contents_text = '\n\n'.join(contents)
        
        return titles_text, contents_text
    
if __name__ == "__main__":
    import asyncio
    
    async def main():
        id = 7  # 替换为实际的分组ID
        titles, contents = await get_grouped_news(id)
        print("-"*50+"Titles"+"-"*50)
        print(titles)
        print("-"*50+"Contents"+"-"*50)
        print(contents)
    
    asyncio.run(main())