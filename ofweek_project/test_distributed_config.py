# -*- coding: UTF-8 -*-
"""测试分布式配置是否正确"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.project import get_settings

def test_distributed_config():
    """测试分布式配置"""
    print("正在加载配置...")
    settings = get_settings()
    
    print("\n=== 配置信息 ===")
    print(f"项目名称: {settings.get('PROJECT_NAME')}")
    print(f"运行模式: {settings.get('RUN_MODE')}")
    print(f"并发数: {settings.get('CONCURRENCY')}")
    print(f"下载延迟: {settings.get('DOWNLOAD_DELAY')}")
    print(f"过滤器类: {settings.get('FILTER_CLASS')}")
    print(f"队列类型: {settings.get('QUEUE_TYPE')}")
    print(f"Redis URL: {settings.get('REDIS_URL')}")
    
    # 检查是否为分布式配置
    is_distributed = (
        settings.get('RUN_MODE') == 'distributed' and
        'aioredis_filter' in settings.get('FILTER_CLASS') and
        settings.get('QUEUE_TYPE') == 'redis'
    )
    
    print(f"\n=== 配置验证 ===")
    if is_distributed:
        print("✅ 配置正确，已启用分布式模式")
        return True
    else:
        print("❌ 配置错误，未启用分布式模式")
        return False

if __name__ == '__main__':
    test_distributed_config()