#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试多个SPIDER_MODULES目录的支持
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 添加ofweek_standalone到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples', 'ofweek_standalone'))

from crawlo.crawler_process import CrawlerProcess
from crawlo.spider import get_spider_names


def test_multiple_spider_modules():
    """测试多个SPIDER_MODULES目录的支持"""
    print("测试多个SPIDER_MODULES目录的支持...")
    
    # 模拟包含多个目录的SPIDER_MODULES配置
    spider_modules = ['ofweek_standalone.spiders', 'ofweek_standalone.new_spiders']
    
    # 创建CrawlerProcess实例
    process = CrawlerProcess(spider_modules=spider_modules)
    
    # 检查是否注册了爬虫
    spider_names = process.get_spider_names()
    print(f"已注册的爬虫: {spider_names}")
    
    # 验证期望的爬虫是否已注册
    expected_spider = 'of_week_standalone'
    if expected_spider in spider_names:
        print(f"✅ 成功: 爬虫 '{expected_spider}' 已注册")
        return True
    else:
        print(f"❌ 失败: 爬虫 '{expected_spider}' 未找到")
        return False


def test_settings_with_multiple_spider_modules():
    """测试settings中配置多个SPIDER_MODULES目录"""
    print("\n测试settings中配置多个SPIDER_MODULES目录...")
    
    # 创建模拟的settings对象
    class MockSettings:
        def get(self, key, default=None):
            if key == 'SPIDER_MODULES':
                return ['ofweek_standalone.spiders', 'ofweek_standalone.new_spiders']
            return default
    
    settings = MockSettings()
    
    # 创建CrawlerProcess实例
    process = CrawlerProcess(settings=settings)
    
    # 检查是否注册了爬虫
    spider_names = process.get_spider_names()
    print(f"已注册的爬虫: {spider_names}")
    
    return True


if __name__ == '__main__':
    print("开始测试多个SPIDER_MODULES目录的支持...\n")
    
    # 测试显式传递多个spider_modules参数
    success1 = test_multiple_spider_modules()
    
    # 测试从settings中读取多个spider_modules配置
    success2 = test_settings_with_multiple_spider_modules()
    
    if success1 and success2:
        print("\n🎉 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)