#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("Testing RedisDedupPipeline loading...")

try:
    # 测试直接导入
    from crawlo.pipelines import RedisDedupPipeline
    print("✓ Direct import successful")
    
    # 测试通过 load_class 导入
    from crawlo.project import load_class
    cls = load_class('crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
    print("✓ load_class import successful")
    print(f"  Class: {cls}")
    
    # 测试创建实例
    # 注意：这需要 Redis 服务器运行
    print("✓ RedisDedupPipeline loading test completed successfully")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()