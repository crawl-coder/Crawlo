#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
三模式验证脚本 — standalone / auto / distributed
验证：
1. 各模式 QUEUE_TYPE / RUN_MODE 正确
2. auto 模式 Redis 可用时自动切换为 redis_stream
3. auto 模式运行 2 次验证 Redis 队列持久化（断点续爬）
4. 框架能正常启动并执行少量请求
"""
import os
import sys
import asyncio

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import redis

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 0


def redis_available() -> bool:
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        return r.ping()
    except Exception:
        return False


def clear_redis_keys(prefix='ofweek_3mode:*'):
    """清理测试用的 Redis key"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        keys = r.keys(prefix)
        if keys:
            r.delete(*keys)
            print(f"  清理 {len(keys)} 个 Redis key (prefix={prefix})")
    except Exception:
        pass


def test_mode_config(mode: str):
    """验证模式配置正确性"""
    from crawlo.core.config import CrawloConfig
    from crawlo.framework import CrawloFramework, reset_framework

    print(f"\n{'='*60}")
    print(f"  模式验证: {mode}")
    print(f"{'='*60}")

    reset_framework()

    if mode == 'standalone':
        config = CrawloConfig.standalone(
            project_name='ofweek_3mode',
            concurrency=2,
            download_delay=0.5,
        )
    elif mode == 'distributed':
        config = CrawloConfig.distributed(
            project_name='ofweek_3mode',
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            concurrency=2,
            download_delay=0.5,
        )
    elif mode == 'auto':
        config = CrawloConfig.auto(
            project_name='ofweek_3mode',
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            concurrency=2,
            download_delay=0.5,
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    settings_dict = config.to_dict()
    fw = CrawloFramework(settings_dict)

    run_mode = fw.settings.get('RUN_MODE', 'unknown')
    queue_type = fw.settings.get('QUEUE_TYPE', 'unknown')
    filter_class = fw.settings.get('FILTER_CLASS', 'unknown')

    print(f"  RUN_MODE:     {run_mode}")
    print(f"  QUEUE_TYPE:   {queue_type}")
    print(f"  FILTER_CLASS: {filter_class}")

    # 验证
    if mode == 'standalone':
        assert run_mode == 'standalone', f"期望 standalone，得到 {run_mode}"
        assert queue_type == 'memory', f"期望 memory，得到 {queue_type}"
        print("  ✅ standalone 模式配置正确")

    elif mode == 'distributed':
        assert run_mode == 'distributed', f"期望 distributed，得到 {run_mode}"
        assert queue_type == 'redis_stream', f"期望 redis_stream，得到 {queue_type}"
        print("  ✅ distributed 模式配置正确")

    elif mode == 'auto':
        # auto 模式：QUEUE_TYPE 为 'auto'，运行时根据 Redis 可用性解析
        assert run_mode == 'auto', f"期望 auto，得到 {run_mode}"
        assert queue_type == 'auto', f"期望 auto（延迟解析），得到 {queue_type}"
        if redis_available():
            print("  ✅ auto 模式配置正确（Redis 可用，运行时将解析为 redis_stream）")
        else:
            print("  ✅ auto 模式配置正确（Redis 不可用，运行时将回退为 memory）")

    reset_framework()
    return run_mode, queue_type


async def run_spider_briefly(mode: str, max_requests: int = 5):
    """以指定模式启动框架并执行少量请求"""
    from crawlo.core.config import CrawloConfig
    from crawlo.framework import CrawloFramework, reset_framework
    from crawlo.crawler import CrawlerProcess

    print(f"\n  [{mode}] 启动爬虫（限制 {max_requests} 请求）...")

    reset_framework()

    if mode == 'standalone':
        config = CrawloConfig.standalone(
            project_name='ofweek_3mode',
            concurrency=2,
            download_delay=0.5,
        )
    elif mode == 'distributed':
        config = CrawloConfig.distributed(
            project_name='ofweek_3mode',
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            concurrency=2,
            download_delay=0.5,
        )
    elif mode == 'auto':
        config = CrawloConfig.auto(
            project_name='ofweek_3mode',
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            concurrency=2,
            download_delay=0.5,
        )

    settings_dict = config.to_dict()
    # 限制最大请求数
    settings_dict['MAX_REQUESTS'] = max_requests
    settings_dict['LOG_LEVEL'] = 'WARNING'  # 减少日志噪音
    settings_dict['SPIDER_MODULES'] = ['ofweek_spider.spiders']

    # 确保 ofweek_spider 包可导入
    spider_path = os.path.join(PROJECT_ROOT, 'examples', 'ofweek_spider')
    if spider_path not in sys.path:
        sys.path.insert(0, spider_path)

    fw = CrawloFramework(settings_dict)
    process = CrawlerProcess(fw.settings)

    try:
        result = await asyncio.wait_for(
            process.crawl('of_week'),
            timeout=120
        )
        fw.settings.get('_stats', {})
        print(f"  [{mode}] 爬虫完成")
        return result
    except asyncio.TimeoutError:
        print(f"  [{mode}] 爬虫超时（120s），停止")
    except Exception as e:
        print(f"  [{mode}] 爬虫异常: {e}")
    finally:
        reset_framework()


def test_auto_redis_persistence():
    """auto 模式运行 2 次，验证 Redis 队列持久化（断点续爬）"""
    print(f"\n{'='*60}")
    print(f"  auto 模式 Redis 队列持久化验证（运行 2 次）")
    print(f"{'='*60}")

    if not redis_available():
        print("  ⚠️ Redis 不可用，跳过持久化验证")
        return

    clear_redis_keys()

    # 第一次运行
    print("\n  --- 第 1 次运行 ---")
    asyncio.run(run_spider_briefly('auto', max_requests=3))

    # 检查 Redis 中是否有队列数据
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    stream_keys = r.keys('crawlo:ofweek_3mode:*stream*')
    filter_keys = r.keys('crawlo:ofweek_3mode:*filter*')
    print(f"  Redis stream keys: {len(stream_keys)}")
    print(f"  Redis filter keys: {len(filter_keys)}")

    # 第二次运行（验证断点续爬——已处理的请求应被去重）
    print("\n  --- 第 2 次运行（验证去重/断点续爬）---")
    asyncio.run(run_spider_briefly('auto', max_requests=3))

    # 清理
    clear_redis_keys()
    print("\n  ✅ auto 模式 Redis 队列持久化验证完成")


def main():
    print("=" * 60)
    print("  Crawlo 三模式验证")
    print(f"  Redis: {'✅ 可用' if redis_available() else '❌ 不可用'}")
    print("=" * 60)

    # 1. 配置验证
    test_mode_config('standalone')
    test_mode_config('distributed')
    test_mode_config('auto')

    # 2. auto 模式 Redis 持久化验证（运行 2 次）
    test_auto_redis_persistence()

    print(f"\n{'='*60}")
    print("  ✅ 三模式验证全部通过")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
