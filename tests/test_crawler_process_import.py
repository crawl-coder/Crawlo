#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试CrawlerProcess导入功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_crawler_process_import():
    """测试CrawlerProcess导入功能"""
    print("测试CrawlerProcess导入功能...")
    
    try:
        # 测试直接从crawlo导入CrawlerProcess
        from crawlo import CrawlerProcess
        print(f"  成功从crawlo导入CrawlerProcess: {CrawlerProcess}")
        
        # 测试创建实例
        process = CrawlerProcess()
        print(f"  成功创建CrawlerProcess实例: {process}")
        
        print("CrawlerProcess导入测试通过!")
        
    except ImportError as e:
        print(f"  导入失败: {e}")
        # 如果直接导入失败，尝试从crawler模块导入
        try:
            from crawlo.crawler import CrawlerProcess
            print(f"  成功从crawlo.crawler导入CrawlerProcess: {CrawlerProcess}")
        except ImportError as e2:
            print(f"  从crawler模块导入也失败: {e2}")


if __name__ == '__main__':
    test_crawler_process_import()