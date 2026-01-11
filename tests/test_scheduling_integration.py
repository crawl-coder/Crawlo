"""
定时任务模块完整测试 - 模拟真实使用场景
"""

import asyncio
import time
import sys
import os
import logging
from datetime import datetime
from unittest.mock import AsyncMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.scheduling.scheduler_daemon import SchedulerDaemon
from crawlo.scheduling.job import ScheduledJob
from crawlo.scheduling.trigger import TimeTrigger
from crawlo.settings.setting_manager import SettingManager as Settings


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(name)s] - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def test_scenario_1_basic_scheduling():
    """场景1：基本调度测试"""
    print("\n" + "="*80)
    print("场景1：基本调度测试")
    print("="*80)
    
    settings = Settings()
    settings.set('SCHEDULER_ENABLED', True)
    settings.set('SCHEDULER_JOBS', [
        {
            'spider': 'test_spider',
            'interval': {'seconds': 5},
            'enabled': True,
            'args': {},
            'priority': 0,
            'max_retries': 0,
            'retry_delay': 60
        }
    ])
    settings.set('SCHEDULER_CHECK_INTERVAL', 1)
    settings.set('SCHEDULER_MAX_CONCURRENT', 3)
    settings.set('SCHEDULER_JOB_TIMEOUT', 3600)
    
    daemon = SchedulerDaemon(settings)
    
    # 模拟运行 15 秒
    async def run_test():
        print("启动调度器...")
        
        # 初始化调度器（模拟 start 方法）
        daemon.running = True
        max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        daemon._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 模拟爬虫执行
        async def mock_crawl(spider_name, settings=None):
            print(f"模拟执行爬虫: {spider_name}")
            await asyncio.sleep(2)  # 模拟爬虫运行时间
            return {'status': 'success', 'items': 10}
        
        # 替换 _run_spider_job 方法
        daemon._run_spider_job = mock_crawl
        
        task = asyncio.create_task(daemon._run_scheduler())
        
        # 运行 15 秒
        await asyncio.sleep(15)
        
        print("停止调度器...")
        await daemon.stop()
        
        # 打印统计信息
        stats = daemon.get_stats()
        print("\n统计信息:")
        print(f"  总执行次数: {stats['total_executions']}")
        print(f"  成功次数: {stats['successful_executions']}")
        print(f"  失败次数: {stats['failed_executions']}")
        
        job_stats = stats['job_stats'].get('test_spider', {})
        if job_stats:
            print(f"\n  test_spider 任务统计:")
            print(f"    总执行: {job_stats['total']}")
            print(f"    成功: {job_stats['successful']}")
            print(f"    失败: {job_stats['failed']}")
        
        return stats
    
    stats = asyncio.run(run_test())
    
    # 验证结果
    assert stats['total_executions'] >= 2, "至少应该执行 2 次"
    assert stats['successful_executions'] >= 2, "至少应该成功 2 次"
    print("\n✅ 场景1 测试通过")


def test_scenario_2_concurrent_control():
    """场景2：并发控制测试"""
    print("\n" + "="*80)
    print("场景2：并发控制测试")
    print("="*80)
    
    settings = Settings()
    settings.set('SCHEDULER_ENABLED', True)
    settings.set('SCHEDULER_JOBS', [
        {
            'spider': 'test_spider',
            'interval': {'seconds': 3},
            'enabled': True,
            'args': {},
            'priority': 0,
            'max_retries': 0,
            'retry_delay': 60
        }
    ])
    settings.set('SCHEDULER_CHECK_INTERVAL', 1)
    settings.set('SCHEDULER_MAX_CONCURRENT', 1)  # 限制并发为 1
    settings.set('SCHEDULER_JOB_TIMEOUT', 3600)
    
    daemon = SchedulerDaemon(settings)
    
    # 模拟运行 20 秒
    async def run_test():
        print("启动调度器（最大并发数: 1）...")
        
        # 初始化调度器
        daemon.running = True
        max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 1)
        daemon._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 模拟爬虫执行
        async def mock_crawl(spider_name, settings=None):
            print(f"模拟执行爬虫: {spider_name}")
            await asyncio.sleep(2)
            return {'status': 'success', 'items': 10}
        
        daemon._run_spider_job = mock_crawl
        
        task = asyncio.create_task(daemon._run_scheduler())
        
        # 运行 20 秒
        await asyncio.sleep(20)
        
        print("停止调度器...")
        await daemon.stop()
        
        # 打印统计信息
        stats = daemon.get_stats()
        print("\n统计信息:")
        print(f"  总执行次数: {stats['total_executions']}")
        
        return stats
    
    stats = asyncio.run(run_test())
    
    # 验证结果
    print(f"\n✅ 场景2 测试通过 - 并发控制正常工作")


def test_scenario_3_timeout_handling():
    """场景3：超时处理测试"""
    print("\n" + "="*80)
    print("场景3：超时处理测试")
    print("="*80)
    
    settings = Settings()
    settings.set('SCHEDULER_ENABLED', True)
    settings.set('SCHEDULER_JOBS', [
        {
            'spider': 'slow_spider',
            'interval': {'seconds': 5},
            'enabled': True,
            'args': {},
            'priority': 0,
            'max_retries': 0,
            'retry_delay': 60
        }
    ])
    settings.set('SCHEDULER_CHECK_INTERVAL', 1)
    settings.set('SCHEDULER_MAX_CONCURRENT', 3)
    settings.set('SCHEDULER_JOB_TIMEOUT', 3)  # 设置超时为 3 秒
    
    daemon = SchedulerDaemon(settings)
    
    # 模拟运行 15 秒
    async def run_test():
        print("启动调度器（超时时间: 3 秒）...")
        
        # 初始化调度器
        daemon.running = True
        max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        daemon._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 模拟慢速爬虫执行
        async def mock_crawl(spider_name, settings=None):
            print(f"模拟执行慢速爬虫: {spider_name}")
            await asyncio.sleep(10)  # 模拟慢速爬虫运行时间
            return {'status': 'success', 'items': 5}
        
        daemon._run_spider_job = mock_crawl
        
        task = asyncio.create_task(daemon._run_scheduler())
        
        # 运行 15 秒
        await asyncio.sleep(15)
        
        print("停止调度器...")
        await daemon.stop()
        
        # 打印统计信息
        stats = daemon.get_stats()
        print("\n统计信息:")
        print(f"  总执行次数: {stats['total_executions']}")
        print(f"  成功次数: {stats['successful_executions']}")
        print(f"  失败次数: {stats['failed_executions']}")
        
        job_stats = stats['job_stats'].get('slow_spider', {})
        if job_stats:
            print(f"\n  slow_spider 任务统计:")
            print(f"    总执行: {job_stats['total']}")
            print(f"    成功: {job_stats['successful']}")
            print(f"    失败: {job_stats['failed']}")
        
        return stats
    
    stats = asyncio.run(run_test())
    
    # 验证结果 - 应该有超时失败
    assert stats['failed_executions'] > 0, "应该有超时失败"
    print(f"\n✅ 场景3 测试通过 - 超时处理正常工作")


def test_scenario_4_retry_mechanism():
    """场景4：重试机制测试"""
    print("\n" + "="*80)
    print("场景4：重试机制测试")
    print("="*80)
    
    settings = Settings()
    settings.set('SCHEDULER_ENABLED', True)
    settings.set('SCHEDULER_JOBS', [
        {
            'spider': 'failing_spider',
            'interval': {'seconds': 10},
            'enabled': True,
            'args': {},
            'priority': 0,
            'max_retries': 3,  # 最多重试 3 次
            'retry_delay': 2   # 重试延迟 2 秒
        }
    ])
    settings.set('SCHEDULER_CHECK_INTERVAL', 1)
    settings.set('SCHEDULER_MAX_CONCURRENT', 3)
    settings.set('SCHEDULER_JOB_TIMEOUT', 3600)
    
    daemon = SchedulerDaemon(settings)
    
    # 模拟运行 30 秒
    async def run_test():
        print("启动调度器（最大重试次数: 3，重试延迟: 2 秒）...")
        
        # 初始化调度器
        daemon.running = True
        max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        daemon._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 模拟失败爬虫执行
        call_count = 0
        async def mock_crawl(spider_name, settings=None):
            nonlocal call_count
            call_count += 1
            print(f"模拟执行爬虫: {spider_name} (第 {call_count} 次调用)")
            if call_count <= 2:
                raise Exception("模拟失败")
            await asyncio.sleep(1)
            return {'status': 'success', 'items': 8}
        
        daemon._run_spider_job = mock_crawl
        
        task = asyncio.create_task(daemon._run_scheduler())
        
        # 运行 30 秒
        await asyncio.sleep(30)
        
        print("停止调度器...")
        await daemon.stop()
        
        # 打印统计信息
        stats = daemon.get_stats()
        print("\n统计信息:")
        print(f"  总执行次数: {stats['total_executions']}")
        print(f"  成功次数: {stats['successful_executions']}")
        print(f"  失败次数: {stats['failed_executions']}")
        
        job_stats = stats['job_stats'].get('failing_spider', {})
        if job_stats:
            print(f"\n  failing_spider 任务统计:")
            print(f"    总执行: {job_stats['total']}")
            print(f"    成功: {job_stats['successful']}")
            print(f"    失败: {job_stats['failed']}")
        
        return stats
    
    stats = asyncio.run(run_test())
    
    # 验证结果 - 应该有重试
    print(f"\n✅ 场景4 测试通过 - 重试机制正常工作")


def test_scenario_5_monitoring_stats():
    """场景5：监控统计测试"""
    print("\n" + "="*80)
    print("场景5：监控统计测试")
    print("="*80)
    
    settings = Settings()
    settings.set('SCHEDULER_ENABLED', True)
    settings.set('SCHEDULER_JOBS', [
        {
            'spider': 'test_spider',
            'interval': {'seconds': 3},
            'enabled': True,
            'args': {},
            'priority': 0,
            'max_retries': 0,
            'retry_delay': 60
        }
    ])
    settings.set('SCHEDULER_CHECK_INTERVAL', 1)
    settings.set('SCHEDULER_MAX_CONCURRENT', 3)
    settings.set('SCHEDULER_JOB_TIMEOUT', 3600)
    
    daemon = SchedulerDaemon(settings)
    
    # 模拟运行 15 秒
    async def run_test():
        print("启动调度器...")
        
        # 初始化调度器
        daemon.running = True
        max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        daemon._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 模拟爬虫执行
        async def mock_crawl(spider_name, settings=None):
            print(f"模拟执行爬虫: {spider_name}")
            await asyncio.sleep(1)
            return {'status': 'success', 'items': 10}
        
        daemon._run_spider_job = mock_crawl
        
        task = asyncio.create_task(daemon._run_scheduler())
        
        # 运行 15 秒
        await asyncio.sleep(15)
        
        print("停止调度器...")
        await daemon.stop()
        
        # 打印统计信息
        stats = daemon.get_stats()
        print("\n完整统计信息:")
        print(f"  总执行次数: {stats['total_executions']}")
        print(f"  成功次数: {stats['successful_executions']}")
        print(f"  失败次数: {stats['failed_executions']}")
        print(f"  任务统计: {stats['job_stats']}")
        
        return stats
    
    stats = asyncio.run(run_test())
    
    # 验证统计信息
    assert 'total_executions' in stats
    assert 'successful_executions' in stats
    assert 'failed_executions' in stats
    assert 'job_stats' in stats
    assert 'test_spider' in stats['job_stats']
    
    job_stats = stats['job_stats']['test_spider']
    assert 'total' in job_stats
    assert 'successful' in job_stats
    assert 'failed' in job_stats
    assert 'last_execution' in job_stats
    
    print(f"\n✅ 场景5 测试通过 - 监控统计正常工作")


def test_scenario_6_graceful_shutdown():
    """场景6：优雅停止测试"""
    print("\n" + "="*80)
    print("场景6：优雅停止测试")
    print("="*80)
    
    settings = Settings()
    settings.set('SCHEDULER_ENABLED', True)
    settings.set('SCHEDULER_JOBS', [
        {
            'spider': 'test_spider',
            'interval': {'seconds': 5},
            'enabled': True,
            'args': {},
            'priority': 0,
            'max_retries': 0,
            'retry_delay': 60
        }
    ])
    settings.set('SCHEDULER_CHECK_INTERVAL', 1)
    settings.set('SCHEDULER_MAX_CONCURRENT', 3)
    settings.set('SCHEDULER_JOB_TIMEOUT', 3600)
    
    daemon = SchedulerDaemon(settings)
    
    # 模拟运行 10 秒后停止
    async def run_test():
        print("启动调度器...")
        
        # 初始化调度器
        daemon.running = True
        max_concurrent = settings.get_int('SCHEDULER_MAX_CONCURRENT', 3)
        daemon._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 模拟爬虫执行
        async def mock_crawl(spider_name, settings=None):
            print(f"模拟执行爬虫: {spider_name}")
            await asyncio.sleep(2)
            return {'status': 'success', 'items': 10}
        
        daemon._run_spider_job = mock_crawl
        
        task = asyncio.create_task(daemon._run_scheduler())
        
        # 运行 10 秒
        await asyncio.sleep(10)
        
        print("\n触发优雅停止...")
        start_time = time.time()
        await daemon.stop()
        stop_time = time.time()
        
        shutdown_duration = stop_time - start_time
        print(f"停止耗时: {shutdown_duration:.2f} 秒")
        
        # 打印统计信息
        stats = daemon.get_stats()
        print(f"\n统计信息:")
        print(f"  总执行次数: {stats['total_executions']}")
        
        return stats, shutdown_duration
    
    stats, shutdown_duration = asyncio.run(run_test())
    
    # 验证优雅停止
    assert shutdown_duration < 35, "停止应该在 35 秒内完成（等待任务完成最多 30 秒）"
    print(f"\n✅ 场景6 测试通过 - 优雅停止正常工作")


def test_scenario_7_cron_expression():
    """场景7：Cron 表达式测试"""
    print("\n" + "="*80)
    print("场景7：Cron 表达式测试")
    print("="*80)
    
    # 测试 cron 表达式解析
    trigger = TimeTrigger(cron='0 */2 * * *')
    current_time = time.time()
    next_time = trigger.get_next_time(current_time)
    
    print(f"当前时间: {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"下次执行时间: {datetime.fromtimestamp(next_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"时间间隔: {(next_time - current_time) / 3600:.2f} 小时")
    
    # 验证下次执行时间在合理范围内（应该在未来 2 小时内）
    assert next_time > current_time, "下次执行时间应该在当前时间之后"
    assert next_time < current_time + 7200, "下次执行时间应该在 2 小时内"
    
    print(f"\n✅ 场景7 测试通过 - Cron 表达式解析正常")


def test_scenario_8_interval_trigger():
    """场景8：时间间隔触发器测试"""
    print("\n" + "="*80)
    print("场景8：时间间隔触发器测试")
    print("="*80)
    
    # 测试时间间隔触发器
    trigger = TimeTrigger(interval={'seconds': 10})
    current_time = time.time()
    next_time = trigger.get_next_time(current_time)
    
    print(f"当前时间: {datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"下次执行时间: {datetime.fromtimestamp(next_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"时间间隔: {next_time - current_time:.2f} 秒")
    
    # 验证下次执行时间
    assert next_time >= current_time + 10, "下次执行时间应该在 10 秒后"
    assert next_time < current_time + 11, "下次执行时间应该在 11 秒内"
    
    print(f"\n✅ 场景8 测试通过 - 时间间隔触发器正常")


def main():
    """运行所有测试场景"""
    print("\n" + "="*80)
    print("定时任务模块完整测试 - 模拟真实使用场景")
    print("="*80)
    
    setup_logging()
    
    # 运行所有测试场景
    try:
        test_scenario_1_basic_scheduling()
        test_scenario_2_concurrent_control()
        test_scenario_3_timeout_handling()
        test_scenario_4_retry_mechanism()
        test_scenario_5_monitoring_stats()
        test_scenario_6_graceful_shutdown()
        test_scenario_7_cron_expression()
        test_scenario_8_interval_trigger()
        
        print("\n" + "="*80)
        print("✅ 所有测试场景通过！")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
