#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
OffsiteMiddleware 演示文件
演示站点过滤中间件在多个域名情况下的使用
"""

import asyncio
from unittest.mock import Mock
from crawlo.middleware.offsite import OffsiteMiddleware
from crawlo.utils.log import get_logger
from crawlo.settings.setting_manager import SettingManager


class SimpleStats:
    """简单的统计类"""
    def __init__(self):
        self.stats = {}

    def inc_value(self, key, count=1, start=0):
        self.stats[key] = self.stats.setdefault(key, start) + count

    def get_stats(self):
        return self.stats


async def main():
    """主函数"""
    # 创建设置管理器
    settings = SettingManager()
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建统计收集器
    stats = SimpleStats()
    
    # 创建日志记录器
    logger = get_logger('Demo', settings.get('LOG_LEVEL'))
    
    # 创建OffsiteMiddleware实例
    offsite_middleware = OffsiteMiddleware(
        stats=stats,
        log_level=settings.get('LOG_LEVEL'),
        allowed_domains=['ee.ofweek.com', 'www.baidu.com']
    )
    # 编译域名正则表达式
    offsite_middleware._compile_domains()
    
    logger.info("开始演示OffsiteMiddleware在多个域名情况下的使用")
    logger.info(f"允许的域名: {offsite_middleware.allowed_domains}")
    
    # 创建测试请求
    requests = [
        # 这些URL应该被允许
        Mock(url='https://ee.ofweek.com/news/article1.html'),
        Mock(url='https://www.baidu.com/s?wd=test'),
        
        # 这些URL应该被过滤掉
        Mock(url='https://www.google.com/search?q=test'),
        Mock(url='https://github.com/user/repo'),
        
        # 子域名测试 - 这些应该被过滤，因为我们只允许确切的域名
        Mock(url='https://news.ofweek.com/article2.html'),
        Mock(url='https://map.baidu.com/location'),
    ]
    
    logger.info(f"生成了 {len(requests)} 个请求")
    
    # 创建一个模拟的爬虫对象
    spider = Mock()
    
    # 处理每个请求
    allowed_count = 0
    filtered_count = 0
    
    for i, request in enumerate(requests):
        logger.info(f"处理请求 {i+1}: {request.url}")
        try:
            # 应用中间件
            await offsite_middleware.process_request(request, spider)
            
            # 如果没有被过滤
            logger.info(f"  -> 请求被允许: {request.url}")
            allowed_count += 1
        except Exception as e:
            logger.info(f"  -> 请求被过滤: {request.url} (原因: {str(e)})")
            filtered_count += 1
    
    logger.info(f"总结:")
    logger.info(f"  允许的请求数: {allowed_count}")
    logger.info(f"  过滤的请求数: {filtered_count}")
    
    # 输出统计信息
    logger.info("统计信息:")
    for key, value in stats.get_stats().items():
        logger.info(f"  {key}: {value}")


if __name__ == '__main__':
    asyncio.run(main())