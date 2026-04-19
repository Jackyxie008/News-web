import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("backend/data/data.db")


def calculate_heat(authorities_sum, published_time):
    """
    计算分组热度值
    公式: 热度 = 权威性总和 / (发布至今小时数 + 2) ^ 1.8
    """
    try:
        pub_dt = datetime.strptime(published_time, "%Y-%m-%d %H:%M:%S")
        hours_diff = (datetime.now() - pub_dt).total_seconds() / 3600
        heat = float(authorities_sum) / ((hours_diff + 2) ** 1.8)
        # 下限保护: 热度最小值 0.00001，防止下溢为0导致排序混乱
        return max(0.00001, heat)
    except:
        return max(0.00001, float(authorities_sum))


def update_all_heat_values():
    """
    重新计算所有分组的最新热度值并更新到数据库
    每次数据处理完成后调用此函数
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查询所有需要更新热度的分组
    cursor.execute("""
        SELECT g.id, g.published, SUM(n.authority) as total_authority
        FROM grouped_news g
        JOIN news n ON instr(',' || g.news_id || ',', ',' || n.id || ',') > 0
        WHERE g.published IS NOT NULL AND g.published != ''
        GROUP BY g.id
    """)

    updates = []
    for group_id, published, total_authority in cursor.fetchall():
        heat = calculate_heat(total_authority, published)
        updates.append((heat, group_id))

    # 批量更新热度
    cursor.executemany("UPDATE grouped_news SET heat = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()

    print(f"✅ 已更新 {len(updates)} 个分组的热度值")


if __name__ == "__main__":
    update_all_heat_values()