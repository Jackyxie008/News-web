import sqlite3
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

def create_grouped_news_table():
    """创建 grouped_news 表"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grouped_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id TEXT,
            title_en TEXT,
            title_cn TEXT,
            full_text_en TEXT,
            full_text_cn TEXT,
            published TEXT,
            location_en TEXT,
            location_cn TEXT,
            latitude REAL,
            longitude REAL,
            category TEXT,
            keywords_en TEXT,
            keywords_cn TEXT,
            links TEXT,
            vector BLOB
        )
    ''')

    conn.commit()
    conn.close()

def get_all_news_ids():
    """获取所有已经存在于分组中的新闻ID"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT news_id FROM grouped_news")
    rows = cursor.fetchall()
    
    existing_ids = set()
    for row in rows:
        if row[0]:
            for nid in row[0].split(','):
                if nid.strip().isdigit():
                    existing_ids.add(int(nid.strip()))
    
    conn.close()
    return existing_ids

def get_existing_groups_vectors():
    """获取已有分组的ID和中心向量"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, vector FROM grouped_news WHERE vector IS NOT NULL")
    rows = cursor.fetchall()
    
    groups = []
    for group_id, vector_blob in rows:
        if vector_blob:
            vector = np.frombuffer(vector_blob, dtype=np.float32)
            groups.append( (group_id, vector) )
    
    conn.close()
    return groups

def get_new_news_data():
    """只获取还没有被聚类的新新闻数据"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    
    existing_ids = get_all_news_ids()
    
    if existing_ids:
        placeholders = ','.join(['?'] * len(existing_ids))
        query = f"SELECT id, title, full_text, published, link FROM news WHERE id NOT IN ({placeholders})"
        df = pd.read_sql_query(query, conn, params=tuple(existing_ids))
    else:
        df = pd.read_sql_query("SELECT id, title, full_text, published, link FROM news", conn)
    
    conn.close()
    return df

def generate_vectors(df):
    """生成新闻向量"""
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2',
                                cache_folder='backend/models/sentence-transformers')
    texts = df['title'] + ' ' + df['full_text']
    vectors = model.encode(texts, show_progress_bar=False, batch_size=32)
    return vectors

def update_group_news_ids(group_id, new_news_ids, new_links, new_published, new_group_vector=None):
    """向已有分组追加新闻ID，同时加权更新分组中心向量"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取原有的数据
    cursor.execute("SELECT news_id, links, published, vector FROM grouped_news WHERE id = ?", (group_id,))
    row = cursor.fetchone()
    if not row:
        return
    
    existing_news_ids, existing_links, existing_published, existing_vector_blob = row
    
    # 合并新闻ID
    all_news_ids = set()
    existing_count = 0
    if existing_news_ids:
        existing_ids = [nid.strip() for nid in existing_news_ids.split(',') if nid.strip().isdigit()]
        existing_count = len(existing_ids)
        all_news_ids.update(existing_ids)
    all_news_ids.update(map(str, new_news_ids))
    merged_news_ids = ','.join(sorted(all_news_ids, key=int))
    new_count = len(new_news_ids)
    
    # 合并链接
    all_links = set()
    if existing_links:
        all_links.update(existing_links.split(','))
    all_links.update(new_links)
    merged_links = ','.join(all_links)
    
    # 取最早的发布时间
    all_published = [existing_published] if existing_published else []
    all_published.append(new_published)
    merged_published = min(all_published)
    
    # 加权融合向量
    if new_group_vector is not None and existing_vector_blob:
        existing_vector = np.frombuffer(existing_vector_blob, dtype=np.float32)
        # 加权平均: 已有向量权重为已有数量，新向量权重为新增数量
        merged_vector = (existing_vector * existing_count + new_group_vector * new_count) / (existing_count + new_count)
        vector_blob = merged_vector.tobytes()
        
        cursor.execute('''
            UPDATE grouped_news 
            SET news_id = ?, links = ?, published = ?, vector = ?
            WHERE id = ?
        ''', (merged_news_ids, merged_links, merged_published, vector_blob, group_id))
    else:
        cursor.execute('''
            UPDATE grouped_news 
            SET news_id = ?, links = ?, published = ?
            WHERE id = ?
        ''', (merged_news_ids, merged_links, merged_published, group_id))
    
    conn.commit()
    conn.close()

def create_new_group(news_ids, links, published, vector):
    """创建新的分组"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    news_ids_str = ','.join(map(str, news_ids))
    links_str = ','.join(links)
    
    cursor.execute('''
        INSERT INTO grouped_news (news_id, published, links, vector)
        VALUES (?, ?, ?, ?)
    ''', (news_ids_str, published, links_str, vector.tobytes()))
    
    conn.commit()
    conn.close()

def group_news():
    """增量新闻聚类：两阶段算法，先内部聚类再与已有分组匹配"""
    # 创建表
    create_grouped_news_table()

    # 获取新新闻数据
    df = get_new_news_data()

    if df.empty:
        print("✅ 没有新的新闻需要聚类")
        return

    print(f"发现 {len(df)} 条新新闻，开始处理...")

    # 生成新新闻向量
    vectors = generate_vectors(df)
    
    # 获取已有分组
    existing_groups = get_existing_groups_vectors()
    
    SIMILARITY_THRESHOLD = 0.87
    
    # ================== 阶段一：新新闻内部互聚类 ==================
    print("阶段一：新新闻内部聚类...")
    temp_groups = []
    
    for idx, vector in enumerate(vectors):
        news_id = df.iloc[idx]['id']
        link = df.iloc[idx]['link']
        published = df.iloc[idx]['published']
        
        best_group_idx = None
        best_similarity = 0
        
        # 与已经创建的临时组匹配
        for group_idx, (group_vector, _, _, _) in enumerate(temp_groups):
            sim = cosine_similarity(vector.reshape(1, -1), group_vector.reshape(1, -1))[0][0]
            if sim > best_similarity:
                best_similarity = sim
                best_group_idx = group_idx
        
        # 匹配成功则加入临时组
        if best_group_idx is not None and best_similarity >= SIMILARITY_THRESHOLD:
            group_vector, news_ids, links, publishes = temp_groups[best_group_idx]
            news_ids.append(news_id)
            links.append(link)
            publishes.append(published)
            # 更新组中心向量（平均值）
            new_vector = (group_vector * (len(news_ids)-1) + vector) / len(news_ids)
            temp_groups[best_group_idx] = (new_vector, news_ids, links, publishes)
        else:
            # 创建新临时组
            temp_groups.append( (vector, [news_id], [link], [published]) )
    
    print(f"新新闻内部聚类完成，合并为 {len(temp_groups)} 个临时组")
    
    # ================== 阶段二：临时组与已有分组匹配 ==================
    print("阶段二：与已有分组匹配...")
    new_groups_count = 0
    merged_groups_count = 0
    
    for group_vector, news_ids, links, publishes in temp_groups:
        published = min(publishes)
        
        best_group_id = None
        best_similarity = 0
        
        # 与所有已有分组计算相似度
        for group_id, existing_vector in existing_groups:
            sim = cosine_similarity(group_vector.reshape(1, -1), existing_vector.reshape(1, -1))[0][0]
            if sim > best_similarity:
                best_similarity = sim
                best_group_id = group_id
        
        # 超过阈值则合并到已有分组
        if best_group_id is not None and best_similarity >= SIMILARITY_THRESHOLD:
            update_group_news_ids(best_group_id, news_ids, links, published, group_vector)
            merged_groups_count += len(news_ids)
        else:
            # 否则创建新分组
            create_new_group(news_ids, links, published, group_vector)
            new_groups_count += 1
    
    print(f"✅ 增量聚类完成：合并 {merged_groups_count} 条到已有分组，创建 {new_groups_count} 个新分组")

if __name__ == "__main__":
    group_news()