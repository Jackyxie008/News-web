import pandas as pd
from pathlib import Path

def deduplicate_news_list(news_list):
    """
    根据链接查重并去重新闻列表
    
    Args:
        news_list (list): 新闻数据列表，每个元素应包含link字段
        
    Returns:
        tuple: (去重后的新闻列表, 删除的重复新闻数量)
    """
    if not isinstance(news_list, list):
        print("输入数据格式错误，应为列表格式")
        return [], 0
    
    if not news_list:
        return [], 0
    
    # 使用pandas进行去重
    df = pd.DataFrame(news_list)
    
    # 检查是否有link字段
    if 'link' not in df.columns:
        print("数据中缺少link字段，无法去重")
        return news_list, 0
    
    # 记录去重前的数量
    original_count = len(df)
    
    # 根据link字段去重，保留第一次出现的记录
    df_deduplicated = df.drop_duplicates(subset=['link'], keep='first')
    
    # 记录去重后的数量
    deduplicated_count = len(df_deduplicated)
    
    # 计算删除的重复数量
    duplicates_count = original_count - deduplicated_count
    
    # 转换回列表格式
    unique_news = df_deduplicated.to_dict('records')
    
    return unique_news, duplicates_count


if __name__ == "__main__":
    # 示例数据
    sample_news = [
        {"title": "新闻1", "link": "https://example.com/news1"},
        {"title": "新闻2", "link": "https://example.com/news2"},
        {"title": "新闻3", "link": "https://example.com/news1"},  # 重复
        {"title": "新闻4", "link": "https://example.com/news3"},
        {"title": "新闻5", "link": "https://example.com/news2"},  # 重复
    ]
    
    # 去重
    unique_news = deduplicate_news_list(sample_news)[0]
    duplicates_count = deduplicate_news_list(sample_news)[1]
    print(f"去重完成，删除了 {duplicates_count} 条重复新闻")
    print(f"剩余新闻数: {len(unique_news)}")
    print("去重后的新闻列表:")
    for news in unique_news:
        print(f"  - {news['title']}: {news['link']}")
