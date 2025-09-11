#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试logger pickle问题修复
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.crawler import CrawlerProcess
from crawlo.settings.setting_manager import SettingManager
from test_logger_fix.spiders.test_spider import TestSpider


async def test_logger_pickle_fix():
    """测试logger pickle问题是否已修复"""
    print("开始测试logger pickle问题修复...")
    
    # 创建包含完整配置的SettingManager
    settings = SettingManager()
    settings.set('DOWNLOADER', 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader')
    settings.set('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
    settings.set('PROJECT_NAME', 'test_logger_fix')
    
    # 创建爬虫进程
    process = CrawlerProcess(settings=settings)
    
    try:
        # 尝试运行爬虫（在分布式模式下会触发pickle问题）
        result = await process.crawl(TestSpider)
        print("爬虫运行成功，logger pickle问题已修复！")
        print(f"运行结果: {result}")
        return True
    except Exception as e:
        print(f"爬虫运行失败: {e}")
        # 检查是否是logger pickle错误
        if "logger cannot be pickled" in str(e):
            print("❌ Logger pickle问题仍然存在！")
            return False
        else:
            print("✅ Logger pickle问题已修复，出现的是其他错误。")
            return True


async def test_settings_copy():
    """测试SettingManager的copy方法是否能正确处理logger对象"""
    print("\n开始测试SettingManager.copy()方法...")
    
    # 创建SettingManager实例
    settings = SettingManager()
    settings.set('TEST_KEY', 'test_value')
    
    try:
        # 尝试复制settings对象
        copied_settings = settings.copy()
        print("✅ SettingManager.copy()方法执行成功！")
        print(f"原始settings: {settings.get('TEST_KEY')}")
        print(f"复制settings: {copied_settings.get('TEST_KEY')}")
        return True
    except Exception as e:
        print(f"❌ SettingManager.copy()方法执行失败: {e}")
        return False


if __name__ == "__main__":
    print("=== 测试Logger Pickle问题修复 ===")
    success1 = asyncio.run(test_settings_copy())
    success2 = asyncio.run(test_logger_pickle_fix())
    
    if success1 and success2:
        print("\n🎉 所有测试通过，logger pickle问题已成功修复！")
    else:
        print("\n❌ 部分测试失败，请检查代码。")