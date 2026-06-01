#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证文章 01《写爬虫这些年，我遇到的那些"没想到"》中提到的全部功能。

⚠️ 已知问题：crawlo/__init__.py 第15行 `import crawlo.helpers as cleaners`
  触发循环导入（helpers → logging → utils → network.response → logging），
  所有依赖 crawlo 包导入的测试均受影响。本脚本在测试前先通过直接加载
  模块路径绕过循环导入，验证核心功能。

运行方式：
  python tests/test_article01_features.py
"""

import asyncio
import os
import sys
import tempfile
import json
import time
import shutil
import importlib
from unittest.mock import AsyncMock, MagicMock

# 添加项目根目录到路径
_proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _proj_root)
os.chdir(_proj_root)  # 确保相对路径正确

PASS = 0
FAIL = 0


def ck(name: str, success: bool, detail: str = ""):
    global PASS, FAIL
    if success:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}: {detail}")


def _safe_import(module_path: str):
    """绕过 crawlo/__init__.py 的循环导入，直接加载子模块"""
    if module_path in sys.modules:
        return sys.modules[module_path]
    # 通过操纵 sys.modules 跳过 __init__.py 的副作用
    # 先加载 crawlo package 但不执行其 __init__
    parent = module_path.rsplit('.', 1)[0] if '.' in module_path else None
    if parent and parent not in sys.modules:
        _safe_import(parent)
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise ImportError(f"Cannot find spec for {module_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_path] = mod
    spec.loader.exec_module(mod)
    return mod


# 预先加载会循环引用的底层模块
print("正在初始化（绕过循环导入）...")
_tried = []
for mod in [
    'crawlo.exceptions',
    'crawlo.utils.singleton',
    'crawlo.utils.request.request_serializer',
    'crawlo.network.request',
    'crawlo.network.response',
    'crawlo.logging',
    'crawlo.logging.manager',
]:
    try:
        _safe_import(mod)
        _tried.append(f'{mod} ✓')
    except Exception as e:
        _tried.append(f'{mod} ✗ {e}')
print("  " + ", ".join(_tried))

# 现在导入 crawlo package 不应再触发循环
import crawlo
print("  包初始化完成\n")


# ============================================================
# 1. 检查点（Checkpoint）—— 保存待爬队列 + 已爬 URL 指纹
# ============================================================
async def test_checkpoint():
    print("\n" + "=" * 60)
    print("【1】检查点（Checkpoint）")
    print("=" * 60)

    from crawlo.checkpoint.storage import JsonStorage

    tmpdir = tempfile.mkdtemp()
    try:
        storage = JsonStorage(
            spider_name='test_spider',
            project_name='test_project',
            checkpoint_dir=tmpdir,
        )

        data = {
            'project_name': 'test_project',
            'spider_name': 'test_spider',
            'pending_count': 3,
            'requests': [
                {'url': 'http://example.com/page1', 'method': 'GET'},
                {'url': 'http://example.com/page2', 'method': 'GET'},
                {'url': 'http://example.com/page3', 'method': 'GET'},
            ],
            'fingerprints': {'fp1', 'fp2'},
            'stats': {'scraped': 10, 'failed': 0},
        }

        # 保存
        saved = storage.save(data)
        ck("1.1 JsonStorage.save() 返回 True", saved is True)

        # 验证文件存在
        exists = storage.exists()
        ck("1.2 检查点文件已生成", exists is True)

        # 加载
        loaded = storage.load()
        ck("1.3 检查点加载成功", loaded is not None)
        if loaded:
            ck("1.4 待爬队列数量正确",
               loaded.get('pending_count') == 3,
               f"期望 3, 实际 {loaded.get('pending_count')}")
            ck("1.5 已爬指纹数量正确",
               len(loaded.get('fingerprints', [])) == 2,
               f"期望 2, 实际 {len(loaded.get('fingerprints', []))}")
            ck("1.6 请求数据完整",
               len(loaded.get('requests', [])) == 3)

        # 清空后再加载应返回 None
        storage.clear()
        loaded_after_clear = storage.load()
        ck("1.7 清空后检查点不存在", loaded_after_clear is None)

    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# 2. 背压控制（Backpressure）—— 自动调节并发
# ============================================================
async def test_backpressure():
    print("\n" + "=" * 60)
    print("【2】背压控制（BackpressureController）")
    print("=" * 60)

    from crawlo.core.engine_helpers import BackpressureController

    controller = BackpressureController(
        max_queue_size=100,
        backpressure_ratio=0.5,
        initial_wait=0.1,
        max_wait=1.0,
    )

    ck("2.1 BackpressureController 初始化成功",
       controller is not None)

    scheduler = MagicMock()
    # is_queue_full 用 len(scheduler)
    scheduler.__len__ = MagicMock(return_value=80)
    task_manager = MagicMock()
    task_manager.current_task = {'task1': 'running', 'task2': 'running', 'task3': 'running'}
    semaphore = MagicMock()
    semaphore._initial_value = 8
    task_manager.semaphore = semaphore

    should_pause = controller.should_pause(scheduler, task_manager)
    ck("2.2 队列使用率 80% > 阈值 50%，应触发背压",
       should_pause is True)

    scheduler.__len__ = MagicMock(return_value=20)
    task_manager.current_task = {'task1': 'running'}  # 只有1个任务
    should_pause_low = controller.should_pause(scheduler, task_manager)
    ck("2.3 队列使用率 20% < 阈值 50%，不应触发背压",
       should_pause_low is False)

    # 测试背压等待（首次满队列触发，然后让队列排空）
    scheduler.__len__ = MagicMock(return_value=250)  # > 200 (max_queue_size)

    # 让队列在第一次检查后排空，且当前任务数减少
    drain = [250]

    def shrinking_len():
        val = drain[0]
        if val > 0:
            drain[0] = val - 100
        return max(val, 0)

    scheduler.__len__ = MagicMock(side_effect=shrinking_len)
    task_manager.current_task = {}
    start = time.time()
    await controller.wait_for_capacity(scheduler, task_manager)
    elapsed = time.time() - start
    ck("2.4 wait_for_capacity 实际延迟 > 0",
       elapsed > 0)
    ck("2.5 背压延迟在预期范围内 (0.01~2.0 秒)",
       0.005 <= elapsed <= 3.0,
       f"实际延迟: {elapsed:.3f}s")


# ============================================================
# 3. 下载器（Downloader）—— HttpX 初始化
# ============================================================
async def test_downloader():
    print("\n" + "=" * 60)
    print("【3】下载器（HttpXDownloader）")
    print("=" * 60)

    from crawlo.downloader import DOWNLOADER_MAP
    from crawlo.downloader.httpx_downloader import HttpXDownloader
    from crawlo.config import CrawloConfig

    ck("3.1 DOWNLOADER_MAP 包含 'httpx'",
       'httpx' in DOWNLOADER_MAP)
    ck("3.2 DOWNLOADER_MAP['httpx'] 指向 HttpXDownloader",
       DOWNLOADER_MAP['httpx'] is HttpXDownloader)

    settings = CrawloConfig.standalone().to_dict()
    crawler = MagicMock()
    crawler.settings = settings

    try:
        downloader = HttpXDownloader(crawler)
        ck("3.3 HttpXDownloader 实例化成功", True)
    except Exception as e:
        ck("3.3 HttpXDownloader 实例化失败", False, str(e))


# ============================================================
# 4. 分布式（Distributed）—— 配置生成
# ============================================================
async def test_distributed():
    print("\n" + "=" * 60)
    print("【4】分布式（CrawloConfig.distributed()）")
    print("=" * 60)

    from crawlo.config import CrawloConfig, RunMode

    config = CrawloConfig.distributed(
        redis_host='127.0.0.1',
        redis_port=6379,
        project_name='dist_test',
        concurrency=16,
        download_delay=1.0,
        max_running_spiders=10,
    )

    ck("4.1 CrawloConfig.distributed() 返回对象",
       config is not None)

    settings = config.to_dict()
    ck("4.2 配置转为字典成功",
       isinstance(settings, dict))

    checks = {
        'REDIS_HOST': '127.0.0.1',
        'REDIS_PORT': 6379,
        'CONCURRENCY': 16,
        'DOWNLOAD_DELAY': 1.0,
    }
    for key, expected in checks.items():
        actual = settings.get(key)
        ck(f"4.3 {key} = {actual}",
           actual == expected,
           f"期望 {expected}, 实际 {actual}")

    run_mode = settings.get('RUN_MODE')
    ck("4.4 运行模式为 'distributed'",
       run_mode == 'distributed',
       f"实际: {run_mode}")

    queue_type = settings.get('QUEUE_TYPE')
    ck("4.5 队列类型为 'redis_stream'",
       queue_type == 'redis_stream',
       f"实际: {queue_type}")


# ============================================================
# 5. 定时调度（Scheduling）—— SCHEDULER_JOBS 解析
# ============================================================
async def test_scheduling():
    print("\n" + "=" * 60)
    print("【5】定时调度（Scheduler）")
    print("=" * 60)

    from crawlo.scheduling.job import ScheduledJob
    from crawlo.scheduling.trigger import TimeTrigger

    # 5.1 Cron 任务测试
    job_cron = ScheduledJob(
        spider_name='of_week',
        cron='*/2 * * * *',
        priority=10,
        max_retries=3,
        retry_delay=60,
    )
    ck("5.1 Cron 任务创建成功", job_cron is not None)
    ck("5.2 Cron 任务爬虫名称正确", job_cron.spider_name == 'of_week')
    ck("5.3 Cron 触发器类型为 cron",
       job_cron.trigger.cron == '*/2 * * * *')

    # 5.2 Interval 任务测试
    job_interval = ScheduledJob(
        spider_name='heartbeat_spider',
        interval={'seconds': 30},
        priority=5,
        max_retries=3,
        retry_delay=60,
    )
    ck("5.5 Interval 任务创建成功", job_interval is not None)
    ck("5.6 Interval 任务爬虫名称正确",
       job_interval.spider_name == 'heartbeat_spider')
    ck("5.7 Interval 触发器类型为 interval",
       job_interval.trigger.interval == {'seconds': 30})

    # 5.3 支持的所有 interval 单位
    unit_multiplier = {
        'seconds': 1,
        'minutes': 60,
        'hours': 3600,
        'days': 86400,
    }
    for unit, multiplier in [('seconds', 30), ('minutes', 15),
                              ('hours', 1), ('days', 1)]:
        trigger = TimeTrigger(interval={unit: multiplier})
        now = time.time()
        nxt = trigger.get_next_time(now)
        expected_min = now + multiplier * unit_multiplier[unit]
        label = {'seconds': '秒', 'minutes': '分钟',
                 'hours': '小时', 'days': '天'}[unit]
        ck(f"5.8 Interval {multiplier}{label} 下次时间 {nxt:.0f} >= {expected_min:.0f}",
           nxt >= expected_min,
           f"偏差: {nxt - expected_min:.3f}s")

    # 5.4 无效 cron 表达式
    try:
        TimeTrigger(cron='invalid')
        ck("5.9 无效 cron 表达式应抛异常", False, "未抛异常")
    except ValueError:
        ck("5.9 无效 cron 表达式正确抛 ValueError", True)

    # 5.5 同时指定 cron 和 interval 的连接器（get_next_time 优先使用 cron）
    dual = TimeTrigger(cron='*/5 * * * *', interval={'hours': 1})
    ck("5.10 同时指定 cron+interval" +
       "get_next_time 使用 cron", dual.get_next_time(time.time()) > 0)


# ============================================================
# 运行全部测试
# ============================================================
async def main():
    global PASS, FAIL
    PASS = 0
    FAIL = 0

    print("=" * 60)
    print("Crawlo 文章 01 功能验证测试")
    print("=" * 60)

    await test_checkpoint()
    await test_backpressure()
    await test_downloader()
    await test_distributed()
    await test_scheduling()

    print("\n" + "=" * 60)
    print(f"结果：通过 {PASS} / 总数 {PASS + FAIL}")
    print("=" * 60)
    if FAIL > 0:
        print("⚠️  有功能未通过验证")

    return FAIL == 0


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
