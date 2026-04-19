import sqlite3
import pandas as pd
from pathlib import Path

def fix_all_groups():
    """
    修复所有分组的links和image_url字段
    修复之前BUG导致图片丢失的问题
    按照最新格式重新生成所有数据
    """
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 开始修复所有分组的链接和图片...")
    
    # 1. 获取所有分组
    cursor.execute("SELECT id, news_id FROM grouped_news")
    groups = cursor.fetchall()
    
    total = len(groups)
    fixed = 0
    
    for group_id, news_id_str in groups:
        if not news_id_str:
            continue
            
        news_ids = [int(nid.strip()) for nid in news_id_str.split(',') if nid.strip().isdigit()]
        
        if not news_ids:
            continue
            
        placeholders = ','.join(['?'] * len(news_ids))
        
        # 2. 查询该分组下所有新闻的来源、链接、权威性、图片
        query = f"""
            SELECT source, link, authority, image_url
            FROM news 
            WHERE id IN ({placeholders})
            ORDER BY authority DESC
        """
        
        df = pd.read_sql_query(query, conn, params=tuple(news_ids))
        
        if df.empty:
            continue
            
        # 3. 生成links字段: 来源,链接,来源,链接...
        links_parts = []
        seen_links = set()
        
        for _, row in df.iterrows():
            if row['link'] not in seen_links:
                seen_links.add(row['link'])
                links_parts.append(row['source'])
                links_parts.append(row['link'])
        
        merged_links = ','.join(links_parts)
        
        # 4. 选择权威性最高的有图片的新闻
        best_image_url = None
        best_image_source = None
        
        for _, row in df.iterrows():
            if row['image_url'] and pd.notna(row['image_url']) and row['image_url'].strip() != '':
                best_image_url = row['image_url']
                best_image_source = row['source']
                break
        
        # 5. 生成image_url字段: 来源,图片链接
        if best_image_url and best_image_source:
            merged_image = f"{best_image_source},{best_image_url}"
        else:
            merged_image = ""
                
        # 6. 更新到数据库
        cursor.execute("""
            UPDATE grouped_news 
            SET links = ?, image_url = ?
            WHERE id = ?
        """, (merged_links, merged_image, group_id))
        
        fixed += 1
        if fixed % 10 == 0:
            print(f"✅ 已修复 {fixed}/{total} 个分组")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 修复完成！总共修复了 {fixed} 个分组")
    print("✅ 所有分组的links字段现在都是正确的来源+链接交替格式")
    print("✅ 所有分组的image_url字段现在都是正确的来源+图片链接格式")

if __name__ == "__main__":
    fix_all_groups()