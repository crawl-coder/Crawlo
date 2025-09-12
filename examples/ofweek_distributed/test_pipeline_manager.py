#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("Testing PipelineManager in framework environment...")

try:
    # 模拟框架环境
    os.chdir(project_root)
    
    # 加载设置
    from crawlo.project import get_settings
    settings = get_settings()
    
    # 创建模拟的 crawler 对象
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
    
    crawler = MockCrawler(settings)
    
    # 测试 PipelineManager
    from crawlo.pipelines.pipeline_manager import PipelineManager
    
    # 获取管道配置
    pipelines = settings.get_list('PIPELINES')
    print(f"Pipeline configurations: {pipelines}")
    
    # 创建 PipelineManager
    pm = PipelineManager(crawler)
    print("✓ PipelineManager created successfully")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()