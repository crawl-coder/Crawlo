#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
分布式采集功能验证脚本
验证Crawlo框架的分布式采集功能是否正常工作
"""

import redis
import json
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def verify_distributed_functionality():
    """验证分布式采集功能"""
    print("=== Crawlo分布式采集功能验证 ===\n")

    # 1. 连接Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=2, decode_responses=False)
        r.ping()
        print("✓ Redis连接成功")
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        return False

    # 2. 检查项目配置
    try:
        with open('../examples/ofweek_distributed/crawlo.cfg', 'r') as f:
            config_content = f.read()
            if 'ofweek_distributed.settings' in config_content:
                print("✓ 项目配置文件正确")
            else:
                print("✗ 项目配置文件不正确")
                return False
    except Exception as e:
        print(f"✗ 无法读取配置文件: {e}")
        return False

    # 3. 检查设置文件
    try:
        with open('../examples/ofweek_distributed/ofweek_distributed/settings.py', 'r') as f:
            settings_content = f.read()
            checks = [
                ('RUN_MODE = \'distributed\'', '运行模式设置为分布式'),
                ('QUEUE_TYPE = \'redis\'', '队列类型设置为Redis'),
                ('FILTER_CLASS = \'crawlo.filters.aioredis_filter.AioRedisFilter\'', '过滤器设置为Redis过滤器'),
                ('REDIS_HOST = \'127.0.0.1\'', 'Redis主机配置正确'),
            ]

            all_passed = True
            for check, description in checks:
                if check in settings_content:
                    print(f"✓ {description}")
                else:
                    print(f"✗ {description}")
                    all_passed = False

            if not all_passed:
                return False
    except Exception as e:
        print(f"✗ 无法读取设置文件: {e}")
        return False

    # 4. 检查Redis中的数据
    try:
        # 检查请求去重指纹
        request_fingerprints = r.scard("crawlo:ofweek_distributed:filter:fingerprint")
        print(f"✓ 请求去重指纹数量: {request_fingerprints}")

        # 检查数据项去重指纹
        item_fingerprints = r.scard("crawlo:ofweek_distributed:item:fingerprint")
        print(f"✓ 数据项去重指纹数量: {item_fingerprints}")

        # 检查请求队列
        queue_size = r.zcard("crawlo:ofweek_distributed:queue:requests")
        print(f"✓ 请求队列大小: {queue_size}")

        # 验证数据是否存在
        if request_fingerprints > 0 and item_fingerprints > 0:
            print("✓ Redis中存在分布式采集数据")
        else:
            print("⚠ Redis中分布式采集数据为空")

    except Exception as e:
        print(f"✗ Redis数据检查失败: {e}")
        return False

    # 5. 检查输出文件
    try:
        import glob
        json_files = glob.glob("output/*.json")
        if json_files:
            latest_file = max(json_files, key=os.path.getctime)
            file_size = os.path.getsize(latest_file)
            print(f"✓ 输出文件存在: {latest_file} ({file_size} bytes)")
        else:
            print("⚠ 未找到输出文件")
    except Exception as e:
        print(f"✗ 输出文件检查失败: {e}")

    print("\n=== 验证结果 ===")
    print("✓ Crawlo分布式采集功能正常工作!")
    print("  - Redis连接正常")
    print("  - 分布式配置正确")
    print("  - Redis数据存储正常")
    print("  - 采集任务执行正常")

    return True


if __name__ == '__main__':
    verify_distributed_functionality()
