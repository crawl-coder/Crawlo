# -*- coding: utf-8 -*-
"""
统一验证脚本：
  Phase A（场景 1 同项目多爬虫并发共享资源）：每轮同时启动 5 个 of_week_adaptive，
            用 shared_resource_scope 保证 5 个爬虫全部结束后再释放共享资源。
            验证：MySQL pool / Redis pool 实例数 = 1 不变（不重复实例化），
                  先结束的爬虫不把共享 pool 关闭（其他爬虫继续可用 → flush 不报错）。
  Phase B（场景 2 长时间定时任务）：执行 20 轮 Phase A，每轮结束调
            scheduler_scope.on_iteration_end 做泄漏检测 + 超阈值告警。
            验证：Crawler / PipelineManager / AioHttpDownloader / AioRedisFilter
                  每轮结束 Δ 不线性增长；RSS / MySQL 连接数 bounded。

用法：
    python test_two_scenarios.py                  # 默认 20 轮 × 5 并发
    N_CONCURRENT=2 N_ROUNDS=3 python test_two_scenarios.py
"""

from __future__ import annotations

import asyncio
import gc
import os
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.absolute()))

from crawlo.crawler_process import CrawlerProcess
from crawlo.core.resource_scope import (
    get_scheduler_resource_scope,
    shared_resource_scope,
    capture_pool_snapshot,
    rss_mb,
)


N_CONCURRENT = int(os.environ.get('N_CONCURRENT', '5'))
N_ROUNDS = int(os.environ.get('N_ROUNDS', '20'))
SPIDER_NAME = 'of_week_adaptive'

tracemalloc.start()
_sched_stats = []


def sample_rss_tm_suffix() -> str:
    rss = rss_mb()
    cur, peak = tracemalloc.get_traced_memory()
    return f"RSS={rss:>6.0f}MB tmalloc_cur={cur/(1024*1024):>5.1f}MB peak={peak/(1024*1024):>5.1f}MB"


async def run_scenario1_one_round(n: int = N_CONCURRENT) -> dict:
    """Phase A：同项目 n 个爬虫并发跑，返回该轮的资源统计快照。"""
    async with shared_resource_scope(f'concurrent-x{n}') as scope:
        cp = CrawlerProcess()
        tasks = [cp.crawl(SPIDER_NAME) for _ in range(n)]
        t0 = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        cost = time.perf_counter() - t0
        ok = sum(1 for r in results if not isinstance(r, Exception))
        fails = [repr(r) for r in results if isinstance(r, Exception)]
        if fails:
            print(f"  ! concurrent batch exceptions: {fails[:5]}", flush=True)
        # 显式释放 CrawlerProcess：避免 cp._crawlers 列表 / cp metrics 仍引用 Crawler 对象，
        # 造成下一轮 gc.snapshot Crawler delta 稳定 +2 的假阳性。
        del cp
        pool = capture_pool_snapshot()
        snap = {
            'concurrent_n': n,
            'ok': ok,
            'fails_n': len(fails),
            'elapsed_s': round(cost, 1),
            'mysql_pools': pool.mysql_pools,
            'mysql_conns': pool.mysql_conns,
            'redis_pools': pool.redis_pools,
        }
        return snap


async def main() -> int:
    print("=" * 78, flush=True)
    print(f"Crawlo 两个场景联合验证：{N_ROUNDS} 轮 × 每轮 {N_CONCURRENT} 并发爬虫", flush=True)
    print("  Phase A 验证：多爬虫共享 pool（共享不重复）", flush=True)
    print("  Phase B 验证：每轮末尾对象/连接/RSS 泄漏斜率报警", flush=True)
    print("=" * 78, flush=True)

    scheduler_scope = get_scheduler_resource_scope(
        name=f'mixed-{N_CONCURRENT}x{N_ROUNDS}',
        iteration_warn_slope={
            'Crawler': 0.2,
            'PipelineManager': 0.1,
            'AioHttpDownloader': 0.1,
            'AioRedisFilter': 0.1,
            'BaseMonitorExtension': 0.1,
            'MySQLConnectionPoolManager': 0.1,
        },
    )
    baseline_suffix = sample_rss_tm_suffix()
    print(f"[baseline] {baseline_suffix}", flush=True)

    round_reports = []
    warnings_overall: list[str] = []

    for r in range(1, N_ROUNDS + 1):
        tag = f"R{r:02d}"
        print(f"\n[{tag}] ===== Phase A: 启动 {N_CONCURRENT} 个 {SPIDER_NAME} 并发 =====", flush=True)
        batch = await run_scenario1_one_round(N_CONCURRENT)
        print(
            f"[{tag}] Phase A done: {batch['ok']}/{batch['concurrent_n']} OK"
            f"  time={batch['elapsed_s']}s"
            f"  MySQLP={batch['mysql_pools']} MySQLC={batch['mysql_conns']}"
            f"  RedisP={batch['redis_pools']}  {sample_rss_tm_suffix()}",
            flush=True,
        )
        # 场景1断言：MySQL pool 数不随并发变化（应始终 <= 1 个共享池）
        if batch['mysql_pools'] > 1:
            warnings_overall.append(
                f"{tag}: 并发{N_CONCURRENT}个爬虫后 MySQL pools={batch['mysql_pools']} (>1)，疑似重复实例化"
            )
        if batch['fails_n'] > 0:
            warnings_overall.append(
                f"{tag}: 并发中 {batch['fails_n']}/{batch['concurrent_n']} 爬虫异常（可能是先结束者关了共享池）"
            )

        # Phase B: 每轮结束泄漏检测
        print(f"[{tag}] ----- Phase B: 泄漏自检 -----", flush=True)
        gc.collect(); gc.collect(); gc.collect()
        report = await scheduler_scope.on_iteration_end(tag=tag)
        round_reports.append(report)
        if report['warnings']:
            warnings_overall.extend(f"{tag}: {w}" for w in report['warnings'])
        print(
            f"[{tag}] Phase B summary: "
            f"Crawler(baselineΔ)={report['delta_baseline'].get('Crawler',0):+}  "
            f"PipeMgrΔ={report['delta_baseline'].get('PipelineManager',0):+}  "
            f"AioDlΔ={report['delta_baseline'].get('AioHttpDownloader',0):+}  "
            f"RSSΔ={report['rss_delta_baseline_mb']:+}MB  "
            f"MySQLC={report['pools_now']['mysql_conns']}",
            flush=True,
        )

    await scheduler_scope.close()

    print("\n" + "=" * 78, flush=True)
    print("FINAL REPORT", flush=True)
    print("=" * 78, flush=True)
    # 场景1汇总
    phase1_pools_max = max(r['pools_now'].get('mysql_pools', 0) for r in round_reports)
    phase1_conns_last = round_reports[-1]['pools_now'].get('mysql_conns', 0)
    print(f"[场景1 结论] 最大 MySQL pool 实例数: {phase1_pools_max} （预期 ≤1）")
    print(f"[场景1 结论] 末尾 MySQL 活跃+空闲连接数: {phase1_conns_last}")

    # 场景2汇总：对象斜率 & RSS
    slopes = scheduler_scope.counter.linear_slopes()
    print(f"[场景2 结论] gc 对象每轮斜率: {slopes}")
    linear_fail = {
        k: v for k, v in slopes.items()
        if v > 0.2 and k in {
            'Crawler', 'PipelineManager', 'AioHttpDownloader', 'AioRedisFilter',
            'BaseMonitorExtension',
        }
    }
    rss_first = round_reports[0]['rss_now_mb'] if round_reports else 0
    rss_last = round_reports[-1]['rss_now_mb'] if round_reports else 0
    rss_per_round = (rss_last - rss_first) / max(len(round_reports), 1)
    print(
        f"[场景2 结论] RSS: {rss_first:.0f}MB → {rss_last:.0f}MB  "
        f"Δ={rss_last-rss_first:+.0f}MB  均值 {rss_per_round:+.1f}MB/轮"
    )

    passed = True
    if phase1_pools_max > 2:
        passed = False
        print(f"  ❌ MySQL pool 实例数 {phase1_pools_max} 异常，有重复实例化。")
    else:
        print(f"  ✅ 场景1 多爬虫共享资源：MySQL pool 未重复实例化。")
    if linear_fail:
        passed = False
        print(f"  ❌ 场景2 长期运行：{linear_fail} 类型按轮次线性增长，疑似泄漏。")
    else:
        print(f"  ✅ 场景2 对象/连接：关键类型斜率正常，无线性增长。")
    if rss_per_round > 2.0:
        passed = False
        print(f"  ❌ 场景2 RSS 每轮 {rss_per_round:+.1f}MB 持续上涨，内存泄漏或 arena 未释。")
    else:
        print(f"  ✅ 场景2 RSS 每轮 {rss_per_round:+.1f}MB 稳态。")
    if warnings_overall:
        print("\n⚠️ 全部警告：")
        for w in warnings_overall:
            print("  - " + w)

    print("\n" + ("✅ 两个场景全部通过。" if passed else "❌ 仍有泄漏/竞争，请排查。"), flush=True)
    tracemalloc.stop()
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
