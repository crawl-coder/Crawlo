#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据项去重Redis Key测试脚本
用于验证RedisDedupPipeline和示例项目中的Redis去重管道是否使用统一的Redis key命名规范
"""
import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.pipelines.redis_dedup_pipeline import RedisDedupPipeline


class MockSettings:
    """模拟设置类"""
    def __init__(self, project_name="test_project"):
        self.project_name = project_name
    
    def get(self, key, default=None):
        if key == 'PROJECT_NAME':
            return self.project_name
        elif key == 'REDIS_HOST':
            return 'localhost'
        elif key == 'REDIS_PORT':
            return 6379
        elif key == 'REDIS_DB':
            return 2
        elif key == 'REDIS_PASSWORD':
            return None
        elif key == 'LOG_LEVEL':
            return 'INFO'
        return default
    
    def getint(self, key, default=0):
        if key == 'REDIS_PORT':
            return 6379
        elif key == 'REDIS_DB':
            return 2
        return default


class MockCrawler:
    """模拟爬虫类"""
    def __init__(self, project_name="test_project"):
        self.settings = MockSettings(project_name)


async def test_item_dedup_redis_key():
    """测试数据项去重Redis key命名规范"""
    print("测试数据项去重Redis key命名规范...")
    
    try:
        # 测试不同的项目名称
        test_cases = [
            {
                "project_name": "books_distributed",
                "expected_key": "crawlo:books_distributed:item:fingerprint",
                "description": "书籍分布式项目"
            },
            {
                "project_name": "api_data_collection",
                "expected_key": "crawlo:api_data_collection:item:fingerprint",
                "description": "API数据采集项目"
            },
            {
                "project_name": "test_project",
                "expected_key": "crawlo:test_project:item:fingerprint",
                "description": "测试项目"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"   {i}. 测试 {test_case['description']}...")
            
            # 测试RedisDedupPipeline
            mock_crawler = MockCrawler(test_case["project_name"])
            pipeline = RedisDedupPipeline.from_crawler(mock_crawler)
            
            # 验证Redis key是否符合规范
            assert pipeline.redis_key == test_case["expected_key"], \
                f"Redis key不匹配: {pipeline.redis_key} != {test_case['expected_key']}"
            
            print(f"      Redis key: {pipeline.redis_key}")
        
        print("数据项去重Redis key命名规范测试通过！")
        return True
        
    except Exception as e:
        print(f"数据项去重Redis key命名规范测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始数据项去重Redis key命名规范测试...")
    print("=" * 50)
    
    try:
        success = test_item_dedup_redis_key()
        
        print("=" * 50)
        if success:
            print("所有测试通过！数据项去重使用统一的Redis key命名规范")
        else:
            print("测试失败，请检查实现")
            return 1
            
    except Exception as e:
        print("=" * 50)
        print(f"测试过程中发生异常: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)