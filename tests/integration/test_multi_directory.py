#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试多个爬虫目录的支持
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 添加ofweek_standalone到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'examples', 'ofweek_standalone'))

def test_multiple_spider_directories():
    """测试多个爬虫目录的支持"""
    print("测试多个爬虫目录的支持...")
    
    # 导入设置
    import examples.ofweek_standalone.ofweek_standalone.settings as settings_module
    
    # 创建设置管理器
    from crawlo.settings.setting_manager import SettingManager
    settings = SettingManager()
    settings.set_settings(settings_module)
    
    # 检查SPIDER_MODULES配置
    spider_modules = settings.get('SPIDER_MODULES')
    print(f"SPIDER_MODULES配置: {spider_modules}")
    
    # 创建CrawlerProcess实例
    from crawlo.crawler import CrawlerProcess
    process = CrawlerProcess(settings=settings)
    
    # 检查是否注册了爬虫
    spider_names = process.get_spider_names()
    print(f"已注册的爬虫: {spider_names}")
    
    # 验证期望的爬虫是否已注册
    expected_spiders = ['of_week_standalone', 'test_spider']
    registered_spiders = []
    
    for spider_name in expected_spiders:
        if spider_name in spider_names:
            print(f"✅ 成功: 爬虫 '{spider_name}' 已注册")
            registered_spiders.append(spider_name)
        else:
            print(f"❌ 失败: 爬虫 '{spider_name}' 未找到")
    
    if len(registered_spiders) == len(expected_spiders):
        print(f"🎉 所有爬虫都已成功注册!")
        return True
    else:
        print(f"⚠️  部分爬虫未注册: {set(expected_spiders) - set(registered_spiders)}")
        return False


if __name__ == '__main__':
    print("开始测试多个爬虫目录的支持...\n")
    
    success = test_multiple_spider_directories()
    
    if success:
        print("\n🎉 测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)