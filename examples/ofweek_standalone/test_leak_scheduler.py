#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试2：定时任务长时间运行资源泄漏检测

方案：
  - 不启动调度器，直接在本进程内连续跑 N 轮 `CrawlerProcess.crawl('of_week')`
    （这等价于调度器反复触发的效果）
  - 每轮结束后采样：
      1. 进程 RSS (psutil)
      2. tracemalloc current/peak
      3. MySQLConnectionPoolManager._instances 大小 + 每个 pool 的 size / freesize
      4. RedisRuntimeContext.connection_pools 大小
      5. gc.get_objects() 里 Crawler / CrawlerProcess / Pipeline 对象的数量
  - 跑完 N 轮后，分析 线性回归斜率 > X 就判定泄漏
"""

import os
import sys
import asyncio
import gc
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlo.crawler_process import CrawlerProcess
from crawlo.utils.db.mysql_connection_pool import MySQLConnectionPoolManager
from crawlo.utils.redis.pool import _resolve_runtime_context


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def _count_instances(type_names):
    """gc 中按 type 名计数（避免强引用）"""
    counts = {n: 0 for n in type_names}
    for obj in gc.get_objects():
        try:
            name = type(obj).__name__
            if name in counts:
                counts[name] += 1
        except Exception:
            pass
    return counts


def _snapshot(round_idx: int, series: dict):
    """采样并写入 series dict"""
    series['round'].append(round_idx)
    series['rss_mb'].append(_rss_mb())

    cur, peak = tracemalloc.get_traced_memory()
    series['tmalloc_cur_mb'].append(cur / 1024 / 1024)
    series['tmalloc_peak_mb'].append(peak / 1024 / 1024)

    stats = MySQLConnectionPoolManager.get_pool_stats()
    series['mysql_pool_count'].append(stats['total_pools'])
    total_size = 0
    total_used = 0
    for info in stats['pools'].values():
        total_size += info.get('size', 0)
        total_used += info.get('used', 0)
    series['mysql_total_conns'].append(total_size)
    series['mysql_used_conns'].append(total_used)

    ctx = _resolve_runtime_context()
    series['redis_pool_count'].append(len(ctx.connection_pools))

    cnt = _count_instances([
        'Crawler', 'CrawlerProcess', 'CrawloFramework',
        'PipelineManager', 'MySQLPipeline', 'AioRedisFilter',
        'AioHttpDownloader', 'MySQLConnectionPoolManager',
        'SchedulerDaemon',
    ])
    for k, v in cnt.items():
        series[f'gc_{k}'].append(v)


def _print_row(series, idx):
    r = series['round'][idx]
    cols = [
        f"R{r:02d}",
        f"RSS={series['rss_mb'][idx]:.0f}MB",
        f"tmal={series['tmalloc_cur_mb'][idx]:.0f}/{series['tmalloc_peak_mb'][idx]:.0f}MB",
        f"MySQLP={series['mysql_pool_count'][idx]}",
        f"MySQLC={series['mysql_used_conns'][idx]}/{series['mysql_total_conns'][idx]}",
        f"RedisP={series['redis_pool_count'][idx]}",
        f"Crawler={series['gc_Crawler'][idx]}",
        f"PipeMgr={series['gc_PipelineManager'][idx]}",
        f"AioHttpDl={series['gc_AioHttpDownloader'][idx]}",
        f"Filter={series['gc_AioRedisFilter'][idx]}",
    ]
    return "  ".join(cols)


def _linear_slope(y_values):
    """计算 y 对 index 的最小二乘斜率（简单判断趋势）"""
    n = len(y_values)
    if n < 3:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(y_values) / n
    num = 0.0
    den = 0.0
    for x, y in zip(xs, y_values):
        num += (x - mx) * (y - my)
        den += (x - mx) ** 2
    if den == 0:
        return 0.0
    return num / den


def _format_conclusion(series) -> list:
    """输出每个指标的结论"""
    lines = []
    checks = [
        ('进程 RSS MB/轮', series['rss_mb'], 2.0),          # 每轮 RSS 增 ≥ 2MB 可疑
        ('tracemalloc_cur MB/轮', series['tmalloc_cur_mb'], 1.5),
        ('MySQL pool_count 趋势', series['mysql_pool_count'], 0.1),
        ('MySQL total_conns 趋势', series['mysql_total_conns'], 0.5),
        ('gc Crawler 增长/轮', series['gc_Crawler'], 0.5),
        ('gc PipelineManager /轮', series['gc_PipelineManager'], 0.5),
        ('gc AioHttpDownloader /轮', series['gc_AioHttpDownloader'], 0.3),
        ('gc AioRedisFilter /轮', series['gc_AioRedisFilter'], 0.3),
    ]
    ok = True
    for name, arr, threshold in checks:
        slope = _linear_slope(arr)
        # 用 首末差 再验证
        diff = arr[-1] - arr[0]
        mark = "✅"
        detail = f"slope={slope:+.3f}/轮 diff={diff:+.2f}"
        # RSS / memory: slope 正且超阈值 => 可疑
        if threshold > 0 and (slope >= threshold or diff >= threshold * max(1, len(arr) / 3)):
            mark = "❌"
            ok = False
        # pool_count / conn: 任何持续增长都可疑
        if name.startswith(('MySQL pool_count', 'MySQL total_conns')):
            if diff > 0 and slope > 0.05:
                mark = "❌"
                ok = False
        lines.append(f"  {mark} {name}: {detail} (阈值 {threshold})")
    return lines, ok


async def leak_test(num_rounds: int = 10):
    tracemalloc.start()
    gc.collect()

    # Header line
    header = (
        f"{'Round':<4} {'RSS':<9} {'tmalloc(c/p)':<15} {'MySQLP':<7} "
        f"{'MySQLC':<11} {'RedisP':<7} {'Crawler':<8} {'PipeMgr':<8} "
        f"{'AioHTTP':<9} {'Filter':<7}"
    )
    print(f"\n===== 长时间泄漏测试: {num_rounds} 轮 =====")
    print(f"  每轮 = CrawlerProcess().crawl('of_week')  完整生命周期")
    print(f"\nHeaders: {header}")

    series: dict = {
        'round': [], 'rss_mb': [], 'tmalloc_cur_mb': [], 'tmalloc_peak_mb': [],
        'mysql_pool_count': [], 'mysql_total_conns': [], 'mysql_used_conns': [],
        'redis_pool_count': [],
        'gc_Crawler': [], 'gc_CrawlerProcess': [], 'gc_CrawloFramework': [],
        'gc_PipelineManager': [], 'gc_MySQLPipeline': [], 'gc_AioRedisFilter': [],
        'gc_AioHttpDownloader': [], 'gc_MySQLConnectionPoolManager': [],
        'gc_SchedulerDaemon': [],
    }

    # baseline
    _snapshot(0, series)
    print("B00: " + _print_row(series, -1))

    for r in range(1, num_rounds + 1):
        cp = CrawlerProcess()
        await cp.crawl('of_week')
        # 主动 gc + 清除框架级全局引用缓存
        del cp
        gc.collect()
        gc.collect()
        gc.collect()
        _snapshot(r, series)
        print(f"R{r:02d}: " + _print_row(series, -1))

    print("\n===== 回归趋势分析 =====")
    conclusions, ok = _format_conclusion(series)
    for line in conclusions:
        print(line)

    # 额外：第一轮 vs 最后一轮关键指标
    print("\n===== 首轮 vs 末轮对比 =====")
    for key in ['rss_mb', 'tmalloc_cur_mb', 'mysql_pool_count', 'mysql_total_conns',
                'redis_pool_count', 'gc_Crawler', 'gc_PipelineManager',
                'gc_AioHttpDownloader', 'gc_AioRedisFilter']:
        first = series[key][0]
        last = series[key][-1]
        sign = '+' if (last - first) > 0 else ''
        print(f"  {key:30s}: {first:>8.2f} → {last:>8.2f} ({sign}{last-first:.2f})")

    print(f"\n===== 最终: {'✅ 无明显泄漏' if ok else '❌ 疑似存在泄漏，需进一步排查'} =====")
    tracemalloc.stop()
    return ok


if __name__ == '__main__':
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    ok = asyncio.run(leak_test(rounds))
    sys.exit(0 if ok else 1)
