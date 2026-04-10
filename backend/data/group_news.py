import sqlite3
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
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
            title TEXT,
            full_text TEXT,
            published TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            keywords TEXT,
            links TEXT
        )
    ''')

    conn.commit()
    conn.close()

def get_news_data():
    """从数据库获取新闻数据，包括链接"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    # 假设 news 表中有 link 或 url 字段，请根据实际字段名修改
    df = pd.read_sql_query("SELECT id, title, full_text, published, link FROM news", conn)
    conn.close()
    return df

def generate_vectors(df):
    """生成新闻向量"""
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2',
                                cache_folder='backend/models/sentence-transformers')
    texts = df['title'] + ' ' + df['full_text']
    vectors = model.encode(texts, show_progress_bar=False)
    return vectors

def cluster_news(vectors):
    """使用 DBSCAN 聚类新闻"""
    clustering = DBSCAN(eps=0.25, min_samples=1, metric='cosine')
    labels = clustering.fit_predict(vectors)
    return labels

def save_grouped_news(df, labels):
    """保存聚类结果到 grouped_news 表"""
    db_path = Path("backend/data/data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 清空原有数据
    cursor.execute("DELETE FROM grouped_news")

    # 按聚类分组
    df['cluster_id'] = labels
    grouped = df.groupby('cluster_id')

    for cluster_id, group in grouped:
        # 收集该组的所有新闻ID
        news_ids = ','.join(map(str, group['id'].tolist()))
        # 收集所有链接，用逗号分隔
        links = ','.join(group['link'].tolist())
        # 取最早的发布时间
        published = group['published'].min()

        cursor.execute('''
            INSERT INTO grouped_news (news_id, published, links)
            VALUES (?, ?, ?)
        ''', (news_ids, published, links))

    conn.commit()
    conn.close()

def group_news():
    """主函数：新闻聚类"""
    # 创建表
    create_grouped_news_table()

    # 获取新闻数据
    df = get_news_data()

    if df.empty:
        print("没有新闻数据可供聚类")
        return

    # 生成向量
    vectors = generate_vectors(df)

    # 聚类
    labels = cluster_news(vectors)

    save_grouped_news(df, labels)
    
    print(f"聚类完成，共生成 {len(set(labels))} 个新闻组")

if __name__ == "__main__":
    group_news()


# VERY IMPORTANT!!!!!!!
# 现在group_news每运行一次会覆盖之前的聚类结果。
# 等后续AI生成聚类新闻标题和正文后，再修改group_news。