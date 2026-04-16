import asyncio
from crawlers.news_crawler import crawler
from data.to_sqlite import csv_to_sqlite
from data.group_news import group_news
from data.process_grouped_data import process_all_added

print("开始执行 main.py...")

print("开始爬取数据...")
asyncio.run(crawler())
print("数据爬取完成！")

print("开始将数据保存到 SQLite 数据库...")
csv_to_sqlite()
print("数据保存完成！")

print("开始对新闻进行聚类...")
group_news()
print("新闻聚类完成！")

# print("开始处理聚类后的新闻数据...")
# asyncio.run(process_all_added())
# print("聚类数据处理完成！")

print("main.py 执行完成！")
