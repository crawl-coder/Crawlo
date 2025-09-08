"""
分布式新闻爬虫运行脚本
演示Crawlo框架的分布式功能：
- Redis队列管理
- 分布式去重
- 多节点协同
- 实时统计监控
- 容错机制
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from crawlo import CrawloConfig
from crawlo.crawler import Crawler
from spiders.distributed_news_spider import DistributedNewsSpider


async def main():
    """主函数：配置并运行分布式爬虫"""
    
    # 创建分布式配置
    config = (CrawloConfig.distributed()
              .set_redis_url('redis://localhost:6379/0')  # Redis连接
              .set_concurrent_requests(20)                # 更高并发
              .set_download_delay(0.5)                   # 更短延迟
              .set_retry_times(5)                        # 更多重试
              .set_timeout(60)                           # 更长超时
              .enable_autothrottle(                      # 自动调节配置
                  start_delay=0.5,
                  max_delay=10,
                  target_concurrency=2.0
              )
              .set_downloader('httpx')                   # 使用httpx（支持HTTP/2）
              .enable_distributed_filter()              # 分布式去重
              .add_pipeline('console')                   # 控制台输出
              .add_pipeline('json', 
                          filename='distributed_news_data.json',
                          append_mode=True)              # 追加模式JSON
              .add_pipeline('mysql',                     # MySQL存储
                          host='localhost',
                          database='crawlo_news',
                          table='news_items')
              .enable_stats()                            # 启用统计
              .set_log_level('INFO')
              .set_stats_interval(30))                   # 30秒统计间隔
    
    # 创建爬虫实例
    crawler = Crawler(config)
    
    # 运行爬虫
    print("启动分布式新闻爬虫...")
    print("Redis连接: redis://localhost:6379/0")
    print("可以启动多个实例进行分布式爬取")
    print("按Ctrl+C停止爬虫")
    
    try:
        await crawler.crawl(DistributedNewsSpider)
    except KeyboardInterrupt:
        print("\n收到停止信号，正在优雅关闭...")
    finally:
        print("\n=== 爬取统计 ===")
        stats = crawler.get_stats()
        print(f"总请求数: {stats.get('request_count', 0)}")
        print(f"成功响应: {stats.get('response_received_count', 0)}")
        print(f"失败请求: {stats.get('request_failed_count', 0)}")
        print(f"数据项数: {stats.get('item_scraped_count', 0)}")


if __name__ == "__main__":
    asyncio.run(main())