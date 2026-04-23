import asyncio
import time
import datetime
from crawlers.news_crawler import crawler
from data.to_sqlite import csv_to_sqlite
from data.group_news import group_news
from data.process_grouped_data import process_all_added
from data.update_heat import update_all_heat_values


# ===================== 运行间隔配置 只需修改这里 =====================
# 运行间隔 单位：分钟 可以修改为任意整数
# 例子：
#  5  = 每5分钟一次  00,05,10,15,20,25,30,35,40,45,50,55 分运行
#  10 = 每10分钟一次 00,10,20,30,40,50 分运行
#  15 = 每15分钟一次 00,15,30,45 分运行
#  20 = 每20分钟一次 00,20,40 分运行
#  30 = 每30分钟一次 00,30 分运行
#  60 = 每60分钟一次 每个小时整点运行
RUN_INTERVAL_MINUTES = 20
# ==================================================================


def get_next_run_time():
    """根据配置的间隔自动计算下一个对齐的运行时间"""
    now = datetime.datetime.now()
    
    # 计算下一个对齐的时间点
    minutes = now.minute
    # 计算需要增加多少分钟才能对齐到间隔
    remainder = minutes % RUN_INTERVAL_MINUTES
    
    if remainder == 0 and now.second == 0:
        # 正好在对齐的时间点，直接等下一个间隔
        add_minutes = RUN_INTERVAL_MINUTES
    else:
        add_minutes = RUN_INTERVAL_MINUTES - remainder
    
    # 计算目标时间
    next_run = now.replace(second=0, microsecond=0)
    next_run += datetime.timedelta(minutes=add_minutes)
    
    return next_run


async def run_pipeline():
    """执行完整的处理流水线"""
    start_time = time.strftime('%Y-%m-%d %H:%M:%S')
    print("\n" + "="*60)
    print(f"⏰ 开始执行任务管道 {start_time}")
    print("="*60)
    
    try:
        print("\n📥 开始爬取数据...")
        await crawler()
        
        print("\n💾 开始保存到数据库...")
        csv_to_sqlite()
        
        print("\n🔗 开始新闻聚类...")
        group_news()
        
        print("\n🔍 开始处理聚类数据...")
        await process_all_added()
        
        print("\n🔥 开始更新所有新闻热度值...")
        update_all_heat_values()
        
        print("\n✅ 本轮执行完成")
        print(f"开始时间：{start_time}")
        print(f"结束时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ 执行过程出现错误: {str(e)}")
        print("   等待下一轮继续执行...")


async def main():
    print(f"🚀 新闻自动处理服务已启动，配置运行间隔: {RUN_INTERVAL_MINUTES} 分钟")
    print(f"📍 程序会自动对齐到整分钟刻度运行")
    print(f"📍 按下 Ctrl+C 可以停止服务\n")
    
    while True:
        # 计算下一次运行时间
        next_run = get_next_run_time()
        now = datetime.datetime.now()
        wait_seconds = (next_run - now).total_seconds()
        
        if wait_seconds < 0:
            # 防止计算异常，最少等1秒
            wait_seconds = 1
        
        print(f"\n⌛ 下一次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            await asyncio.sleep(wait_seconds)
        except asyncio.CancelledError:
            break

        await run_pipeline()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 服务已正常停止")