#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("Testing RedisDedupPipeline loading in framework environment...")

try:
    # 模拟框架中的导入过程
    from crawlo.project import load_class
    
    # 测试不同的导入路径
    test_paths = [
        'crawlo.pipelines.RedisDedupPipeline',
        'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'
    ]
    
    for path in test_paths:
        try:
            print(f"Testing path: {path}")
            cls = load_class(path)
            print(f"  ✓ Success: {cls}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    # 测试直接导入模块
    print("\nTesting direct module import:")
    try:
        import crawlo.pipelines
        print(f"  ✓ Module imported successfully")
        print(f"  Available attributes: {[attr for attr in dir(crawlo.pipelines) if not attr.startswith('_')]}")
        
        # 检查 RedisDedupPipeline 是否存在
        if hasattr(crawlo.pipelines, 'RedisDedupPipeline'):
            print(f"  ✓ RedisDedupPipeline found: {crawlo.pipelines.RedisDedupPipeline}")
        else:
            print(f"  ✗ RedisDedupPipeline not found in module")
    except Exception as e:
        print(f"  ✗ Module import failed: {e}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()