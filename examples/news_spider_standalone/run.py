"""
单机版新闻爬虫运行脚本
演示Crawlo框架的基本功能：
- 单机模式运行
- 多种下载器支持
- 中间件系统
- 数据管道
- 智能配置
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from crawlo import CrawloConfig
from crawlo.crawler import Crawler
from spiders.news_spider import NewsSpider


async def main():
    """主函数：配置并运行单机版爬虫"""
    
    # 创建单机版配置
    config = (CrawloConfig.standalone()
              .set_concurrent_requests(10)  # 并发请求数
              .set_download_delay(1)        # 下载延迟
              .set_retry_times(3)           # 重试次数
              .set_timeout(30)              # 超时时间
              .enable_autothrottle()        # 启用自动调节
              .set_downloader('aiohttp')    # 使用aiohttp下载器
              .add_pipeline('console')      # 添加控制台输出管道
              .add_pipeline('json', filename='news_data.json')  # JSON文件管道
              .add_pipeline('csv', filename='news_data.csv')    # CSV文件管道
              .enable_stats()               # 启用统计
              .set_log_level('INFO'))       # 设置日志级别
    
    # 创建爬虫实例
    crawler = Crawler(config)
    
    # 运行爬虫
    await crawler.crawl(NewsSpider)
    
    print("\n=== 爬取完成 ===")
    print("数据已保存到:")
    print("- news_data.json")
    print("- news_data.csv")
    print("- 控制台输出")


if __name__ == "__main__":
    asyncio.run(main())