#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试SpiderLoader功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.spider_loader import SpiderLoader
from crawlo.settings.setting_manager import SettingManager


def test_spider_loader():
    """测试SpiderLoader基本功能"""
    print("测试SpiderLoader基本功能...")
    
    # 创建一个简单的设置
    settings = SettingManager({
        'SPIDER_MODULES': ['tests.test_spiders'],
        'SPIDER_LOADER_WARN_ONLY': True
    })
    
    # 创建SpiderLoader实例
    loader = SpiderLoader.from_settings(settings)
    
    # 测试list方法
    spider_names = loader.list()
    print(f"发现的爬虫: {spider_names}")
    
    # 测试load方法
    if spider_names:
        spider_name = spider_names[0]
        try:
            spider_class = loader.load(spider_name)
            print(f"成功加载爬虫: {spider_name} -> {spider_class}")
        except KeyError as e:
            print(f"加载爬虫失败: {e}")
    
    # 测试get_all方法
    all_spiders = loader.get_all()
    print(f"所有爬虫: {list(all_spiders.keys())}")
    
    print("测试完成!")


if __name__ == '__main__':
    test_spider_loader()