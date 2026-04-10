import os
import pandas as pd
import sqlite3
from pathlib import Path

def csv_to_sqlite():
    # 创建 SQLite 数据库文件
    db_path = Path("backend/data/data.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 连接到 SQLite 数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建新闻表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            authority INTEGER,
            title TEXT,
            link TEXT,
            published TEXT,
            full_text TEXT,
            image_url TEXT
        )
    ''')

    # 遍历 data_categorized_by_media 目录下所有 .csv 文件
    data_dir = Path("backend/data/data_categorized_by_media")
    csv_files = list(data_dir.glob("*.csv"))

    # 读取所有 CSV 文件并合并数据
    all_data = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            # 只保留需要的列
            df = df[['source', 'authority', 'title', 'link', 'published', 'full_text', 'image_url']]
            all_data.append(df)
        except Exception as e:
            print(f"{csv_file}无数据")

    if all_data:
        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 将数据写入 SQLite 数据库
        for _, row in combined_df.iterrows():
            cursor.execute('''
                INSERT INTO news (source, authority, title, link, published, full_text, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['source'], row['authority'], row['title'], row['link'], row['published'], row['full_text'], row['image_url']))

        # 提交事务
        conn.commit()

    # 关闭连接
    conn.close()

def drop_news_table():
    """删除news表"""
    db_path = Path("backend/data/data.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS news")
        conn.commit()
        print("news表已成功删除")
    except sqlite3.Error as e:
        print(f"删除表时出错: {e}")
    finally:
        if conn:
            conn.close()

def drop_grouped_news_table():
    """删除grouped_news表"""
    db_path = Path("backend/data/data.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS grouped_news")
        conn.commit()
        print("grouped_news表已成功删除")
    except sqlite3.Error as e:
        print(f"删除表时出错: {e}")
    finally:
        if conn:
            conn.close()


def clear_grouped_news_table():
    """清空新闻表中的所有数据并重置ID"""
    db_path = Path("backend/data/data.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM grouped_news")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='grouped_news'")
        conn.commit()
        print("新闻表数据已成功清空，ID已重置")
    except sqlite3.Error as e:
        print(f"清空数据时出错: {e}")
    finally:
        if conn:
            conn.close()

def clear_news_table():
    """清空新闻表中的所有数据并重置ID"""
    db_path = Path("backend/data/data.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='news'")
        conn.commit()
        print("新闻表数据已成功清空，ID已重置")
    except sqlite3.Error as e:
        print(f"清空数据时出错: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # 清空data.db
    clear_news_table()
    clear_grouped_news_table()
    drop_news_table()
    drop_grouped_news_table()
