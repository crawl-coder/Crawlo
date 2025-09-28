#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试管道配置
查看实际的管道配置合并结果
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.settings.setting_manager import SettingManager

def debug_pipelines():
    """调试管道配置"""
    print("调试管道配置合并...")
    print("=" * 50)
    
    # 用户自定义配置
    user_config = {
        'PIPELINES': [
            'myproject.pipelines.CustomPipeline',
        ]
    }
    
    settings = SettingManager(user_config)
    
    # 获取合并后的管道列表
    pipelines = settings.get('PIPELINES')
    
    print("合并后的管道列表:")
    for i, pipeline in enumerate(pipelines):
        print(f"  {i}: {pipeline}")
    
    print()
    print("默认去重管道:")
    dedup_pipeline = settings.get('DEFAULT_DEDUP_PIPELINE')
    print(f"  {dedup_pipeline}")
    
    print()
    print("框架默认管道:")
    default_pipelines = settings.get('PIPELINES', [])  # 直接获取PIPELINES，它已经包含了默认管道
    # 从合并后的管道中移除去重管道，得到框架默认管道
    if dedup_pipeline:
        default_pipelines_without_dedup = [p for p in default_pipelines if p != dedup_pipeline]
        for i, pipeline in enumerate(default_pipelines_without_dedup):
            print(f"  {i}: {pipeline}")
    else:
        for i, pipeline in enumerate(default_pipelines):
            print(f"  {i}: {pipeline}")
    
    print()
    print("自定义管道:")
    custom_pipelines = settings.get('PIPELINES')
    # 从合并后的管道中移除默认管道，得到自定义管道
    default_pipelines_list = [
        'crawlo.pipelines.console_pipeline.ConsolePipeline',
        'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'
    ]
    custom_pipelines_list = [p for p in custom_pipelines if p not in default_pipelines_list]
    for i, pipeline in enumerate(custom_pipelines_list):
        print(f"  {i}: {pipeline}")

if __name__ == "__main__":
    debug_pipelines()