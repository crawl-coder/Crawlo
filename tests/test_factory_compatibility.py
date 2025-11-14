#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试CrawloConfig工厂模式兼容性
"""

import sys
import os
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig


def test_standalone_factory():
    """测试单机模式工厂函数"""
    print("测试单机模式工厂函数...")
    
    try:
        # 创建单机模式配置
        config = CrawloConfig.standalone(
            project_name='ofweek_standalone',
            concurrency=8,
            download_delay=1.0
        )
        
        print(f"配置创建成功")
        print(f"RUN_MODE: {config.get('RUN_MODE')}")
        print(f"QUEUE_TYPE: {config.get('QUEUE_TYPE')}")
        print(f"PROJECT_NAME: {config.get('PROJECT_NAME')}")
        print(f"CONCURRENCY: {config.get('CONCURRENCY')}")
        print(f"DOWNLOAD_DELAY: {config.get('DOWNLOAD_DELAY')}")
        
        # 验证配置是否正确
        assert config.get('RUN_MODE') == 'standalone'
        assert config.get('QUEUE_TYPE') == 'memory'
        assert config.get('PROJECT_NAME') == 'ofweek_standalone'
        assert config.get('CONCURRENCY') == 8
        assert config.get('DOWNLOAD_DELAY') == 1.0
        
        print("✅ 单机模式工厂函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 单机模式工厂函数测试失败: {e}")
        traceback.print_exc()
        return False


def test_distributed_factory():
    """测试分布式模式工厂函数"""
    print("\n测试分布式模式工厂函数...")
    
    try:
        # 创建分布式模式配置
        config = CrawloConfig.distributed(
            redis_host='127.0.0.1',
            redis_port=6379,
            project_name='ofweek_distributed',
            concurrency=16,
            download_delay=0.5
        )
        
        print(f"配置创建成功")
        print(f"RUN_MODE: {config.get('RUN_MODE')}")
        print(f"QUEUE_TYPE: {config.get('QUEUE_TYPE')}")
        print(f"PROJECT_NAME: {config.get('PROJECT_NAME')}")
        print(f"CONCURRENCY: {config.get('CONCURRENCY')}")
        print(f"DOWNLOAD_DELAY: {config.get('DOWNLOAD_DELAY')}")
        print(f"REDIS_HOST: {config.get('REDIS_HOST')}")
        print(f"REDIS_PORT: {config.get('REDIS_PORT')}")
        
        # 验证配置是否正确
        assert config.get('RUN_MODE') == 'distributed'
        assert config.get('QUEUE_TYPE') == 'redis'
        assert config.get('PROJECT_NAME') == 'ofweek_distributed'
        assert config.get('CONCURRENCY') == 16
        assert config.get('DOWNLOAD_DELAY') == 0.5
        assert config.get('REDIS_HOST') == '127.0.0.1'
        assert config.get('REDIS_PORT') == 6379
        
        print("✅ 分布式模式工厂函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 分布式模式工厂函数测试失败: {e}")
        traceback.print_exc()
        return False


def test_auto_factory():
    """测试自动模式工厂函数"""
    print("\n测试自动模式工厂函数...")
    
    try:
        # 创建自动模式配置
        config = CrawloConfig.auto(
            project_name='ofweek_auto',
            concurrency=12,
            download_delay=0.8
        )
        
        print(f"配置创建成功")
        print(f"RUN_MODE: {config.get('RUN_MODE')}")
        print(f"QUEUE_TYPE: {config.get('QUEUE_TYPE')}")
        print(f"PROJECT_NAME: {config.get('PROJECT_NAME')}")
        print(f"CONCURRENCY: {config.get('CONCURRENCY')}")
        print(f"DOWNLOAD_DELAY: {config.get('DOWNLOAD_DELAY')}")
        
        # 验证配置是否正确
        assert config.get('RUN_MODE') == 'auto'
        assert config.get('QUEUE_TYPE') == 'auto'
        assert config.get('PROJECT_NAME') == 'ofweek_auto'
        assert config.get('CONCURRENCY') == 12
        assert config.get('DOWNLOAD_DELAY') == 0.8
        
        print("✅ 自动模式工厂函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 自动模式工厂函数测试失败: {e}")
        traceback.print_exc()
        return False


def test_config_to_dict():
    """测试配置转换为字典"""
    print("\n测试配置转换为字典...")
    
    try:
        # 创建配置
        config = CrawloConfig.standalone(
            project_name='test_project',
            concurrency=4
        )
        
        # 转换为字典
        config_dict = config.to_dict()
        
        print(f"字典转换成功")
        print(f"字典键数量: {len(config_dict)}")
        
        # 验证关键配置项
        assert 'RUN_MODE' in config_dict
        assert 'QUEUE_TYPE' in config_dict
        assert 'PROJECT_NAME' in config_dict
        assert 'CONCURRENCY' in config_dict
        
        print("✅ 配置转换为字典测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置转换为字典测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("开始测试CrawloConfig工厂模式兼容性...")
    print("=" * 50)
    
    tests = [
        test_standalone_factory,
        test_distributed_factory,
        test_auto_factory,
        test_config_to_dict,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_func.__name__} 通过")
            else:
                print(f"✗ {test_func.__name__} 失败")
        except Exception as e:
            print(f"✗ {test_func.__name__} 异常: {e}")
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！CrawloConfig工厂模式兼容性正常。")
        return 0
    else:
        print("部分测试失败，请检查实现。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)