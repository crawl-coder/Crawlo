#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试SPIDER_MODULES配置的自动读取功能
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 添加ofweek_standalone到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples', 'ofweek_standalone'))

from crawlo.crawler import CrawlerProcess
from crawlo.spider import get_spider_names


def test_spider_modules_auto_discovery():
    """测试SPIDER_MODULES配置的自动读取功能"""
    print("测试SPIDER_MODULES配置的自动读取功能...")
    
    # 导入设置
    import examples.ofweek_standalone.ofweek_standalone.settings as settings_module
    
    # 创建设置管理器
    from crawlo.settings.setting_manager import SettingManager
    settings = SettingManager()
    settings.set_settings(settings_module)
    
    # 创建CrawlerProcess实例，不显式传递spider_modules
    process = CrawlerProcess(settings=settings)
    
    # 检查是否自动注册了爬虫
    spider_names = process.get_spider_names()
    print(f"已注册的爬虫: {spider_names}")
    
    # 验证期望的爬虫是否已注册
    expected_spider = 'of_week_standalone'
    if expected_spider in spider_names:
        print(f"✅ 成功: 爬虫 '{expected_spider}' 已自动注册")
        return True
    else:
        print(f"❌ 失败: 爬虫 '{expected_spider}' 未找到")
        return False


def test_crawler_process_with_explicit_spider_modules():
    """测试显式传递spider_modules参数的功能"""
    print("\n测试显式传递spider_modules参数的功能...")
    
    # 显式传递spider_modules参数
    spider_modules = ['ofweek_standalone.spiders']
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


if __name__ == '__main__':
    print("开始测试SPIDER_MODULES配置功能...\n")
    
    # 测试自动发现功能
    success1 = test_spider_modules_auto_discovery()
    
    # 测试显式传递参数功能
    success2 = test_crawler_process_with_explicit_spider_modules()
    
    if success1 and success2:
        print("\n🎉 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)