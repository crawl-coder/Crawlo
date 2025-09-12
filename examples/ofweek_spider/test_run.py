#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试脚本：验证 OfweekSpider 是否能正常运行
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from crawlo.crawler import CrawlerProcess
        print("✅ Crawlo 模块导入成功")
    except Exception as e:
        print(f"❌ Crawlo 模块导入失败: {e}")
        return False
    
    try:
        from ofweek_spider.spiders.OfweekSpider import OfweekSpider
        print("✅ OfweekSpider 导入成功")
    except Exception as e:
        print(f"❌ OfweekSpider 导入失败: {e}")
        return False
    
    try:
        from ofweek_spider.settings_standalone import *
        print("✅ 单机模式配置导入成功")
    except Exception as e:
        print(f"❌ 单机模式配置导入失败: {e}")
        return False
    
    try:
        from ofweek_spider.settings_distributed import *
        print("✅ 分布式模式配置导入成功")
    except Exception as e:
        print(f"❌ 分布式模式配置导入失败: {e}")
        return False
    
    return True

def test_standalone_config():
    """测试单机模式配置"""
    print("\n🔍 测试单机模式配置...")
    
    try:
        from ofweek_spider.settings_standalone import *
        
        # 检查关键配置项
        assert PROJECT_NAME == 'ofweek_spider_standalone'
        assert RUN_MODE == 'standalone'
        assert CONCURRENCY == 4
        assert QUEUE_TYPE == 'memory'
        assert FILTER_CLASS == 'crawlo.filters.memory_filter.MemoryFilter'
        
        print("✅ 单机模式配置验证通过")
        return True
    except Exception as e:
        print(f"❌ 单机模式配置验证失败: {e}")
        return False

def test_distributed_config():
    """测试分布式模式配置"""
    print("\n🔍 测试分布式模式配置...")
    
    try:
        from ofweek_spider.settings_distributed import *
        
        # 检查关键配置项
        assert PROJECT_NAME == 'ofweek_spider_distributed'
        assert RUN_MODE == 'distributed'
        assert CONCURRENCY == 16
        assert QUEUE_TYPE == 'redis'
        assert FILTER_CLASS == 'crawlo.filters.aioredis_filter.AioRedisFilter'
        assert 'redis://' in REDIS_URL
        
        print("✅ 分布式模式配置验证通过")
        return True
    except Exception as e:
        print(f"❌ 分布式模式配置验证失败: {e}")
        return False

def test_spider():
    """测试爬虫类"""
    print("\n🔍 测试爬虫类...")
    
    try:
        from ofweek_spider.spiders.OfweekSpider import OfweekSpider
        
        # 检查爬虫属性
        assert OfweekSpider.name == 'of_week'
        assert 'ee.ofweek.com' in OfweekSpider.allowed_domains
        
        print("✅ 爬虫类验证通过")
        return True
    except Exception as e:
        print(f"❌ 爬虫类验证失败: {e}")
        return False

def test_items():
    """测试数据项"""
    print("\n🔍 测试数据项...")
    
    try:
        from ofweek_spider.items import NewsItem
        
        # 检查数据项字段
        item = NewsItem()
        expected_fields = ['title', 'publish_time', 'url', 'source', 'content']
        for field in expected_fields:
            assert hasattr(item, field)
        
        print("✅ 数据项验证通过")
        return True
    except Exception as e:
        print(f"❌ 数据项验证失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始测试 OfweekSpider 示例项目")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        test_imports,
        test_standalone_config,
        test_distributed_config,
        test_spider,
        test_items
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！项目配置正确。")
        return 0
    else:
        print("❌ 部分测试失败，请检查上述错误。")
        return 1

if __name__ == '__main__':
    sys.exit(main())