#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
分布式采集测试脚本
用于验证分布式采集功能是否正常工作
"""

import asyncio
import sys
import os
import time

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换到项目根目录
os.chdir(project_root)

from crawlo.crawler import CrawlerProcess
from crawlo.utils.log import get_logger

logger = get_logger(__name__)


async def test_distributed_crawling():
    """测试分布式采集功能"""
    logger.info("开始测试分布式采集功能...")

    # 创建爬虫进程并应用配置
    try:
        # 确保 spider 模块被正确导入
        spider_modules = ['ofweek_distributed.spiders']
        process = CrawlerProcess(spider_modules=spider_modules)
        logger.info("爬虫进程初始化成功")

        # 运行指定的爬虫，使用正确的爬虫名称
        result = await process.crawl('of_week_distributed')
        logger.info(f"爬虫运行完成，结果: {result}")

    except Exception as e:
        logger.error(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数"""
    start_time = time.time()
    logger.info("开始分布式采集测试")

    try:
        asyncio.run(test_distributed_crawling())
        end_time = time.time()
        logger.info(f"分布式采集测试完成，耗时: {end_time - start_time:.2f} 秒")
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
