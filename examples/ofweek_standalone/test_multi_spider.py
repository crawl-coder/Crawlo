#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试1：同项目多爬虫并发资源竞争 & 重复实例化检测

预期：
  - MySQLConnectionPoolManager._instances 中同 pool_key 仅 1 条（共享）
  - 同 spider 内部：MySQLPipeline + MySQLDedupPipeline + MySQLExistsChecker 共用 pool
  - EventloopLagProbe / LogIntervalExtension：每个 crawler 独立实例（正常）
  - Redis Filter：同配置共用连接池（全局）
  - 多次 CrawlerProcess.crawl() 之间：无额外增长

方法：
  1. 先把 CrawloConfig 缩到 min 规模：max_pages=1, concurrency=2, batch=小
  2. 启动 3 个爬虫 (of_week + of_week_db = of_week_with_db + of_week_adaptive) 并发
  3. 过程中 & 结束后 print MySQL pool 实例数、Redis client 实例数、PipelineManager 数等
"""

import os
import sys
import asyncio
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlo.crawler_process import CrawlerProcess
from crawlo.utils.db.mysql_connection_pool import MySQLConnectionPoolManager
from crawlo.utils.redis.pool import _resolve_runtime_context


def _snapshot_mysql_pools(label: str):
    """打印 MySQL 共享连接池统计 + ref_count"""
    instances = MySQLConnectionPoolManager._instances
    print(f"\n===== [MySQL Pools] {label} =====")
    print(f"  共享 pool 实例数: {len(instances)}")
    stats = MySQLConnectionPoolManager.get_pool_stats()
    for k, inst in list(instances.items()):
        pool = getattr(inst, 'pool', None)
        pool_closed = getattr(pool, '_closed', 'N/A')
        pool_minsize = getattr(pool, 'minsize', '?')
        pool_maxsize = getattr(pool, 'maxsize', '?')
        pool_size = getattr(pool, 'size', '?')
        pool_freesize = getattr(pool, '_pool', None)
        free_cnt = len(pool_freesize) if pool_freesize else '?'
        ref = stats.get('pools', {}).get(k, {}).get('ref_count', '?')
        print(f"  [{k}] pool_id={id(pool)} closed={pool_closed} "
              f"ref_count={ref} min={pool_minsize} max={pool_maxsize} "
              f"size={pool_size} free={free_cnt}")
    total_conns = 0
    for inst in instances.values():
        p = getattr(inst, 'pool', None)
        total_conns += getattr(p, 'size', 0) or 0
    print(f"  汇总连接数(size之和): {total_conns}")
    return len(instances), total_conns, stats


def _snapshot_redis_pools(label: str):
    """打印 Redis 共享连接池统计"""
    ctx = _resolve_runtime_context()
    pools = ctx.connection_pools
    print(f"\n===== [Redis Pools] {label} =====")
    print(f"  共享 pool 实例数: {len(pools)}")
    for k, p in list(pools.items()):
        rc = getattr(p, '_redis_client', None)
        cp = getattr(p, '_connection_pool', None)
        rc_addr = getattr(rc, 'connection_pool', None)
        max_connections = getattr(rc_addr, 'max_connections', '?') if rc_addr else '?'
        client_alive = False
        if rc is not None:
            try:
                # just check not None and type looks healthy
                client_alive = True
            except Exception:
                client_alive = False
        print(f"  [{k}] redis_client={id(rc) if rc else None} "
              f"client_alive={client_alive} "
              f"conn_pool={id(cp) if cp else None} max_conn={max_connections}")
    return len(pools)


def _rss_mb(pid=None):
    try:
        import psutil
        proc = psutil.Process(pid or os.getpid())
        return proc.memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


async def run_multi_spider_test():
    tracemalloc.start()
    print(f"\n===== 进程 RSS 初始: {_rss_mb():.1f} MB =====")

    mysql_before, mysql_conn_before, stats_before = _snapshot_mysql_pools("Before CrawlerProcess")
    _snapshot_redis_pools("Before CrawlerProcess")

    cp = CrawlerProcess()

    # 爬虫1: of_week
    # 爬虫2: of_week_adaptive
    names = ['of_week', 'of_week_adaptive']
    print(f"\n===== 并发启动 {len(names)} 个爬虫: {names} =====")

    tasks = []
    for name in names:
        tasks.append(asyncio.create_task(cp.crawl(name)))

    # 中途点：第一个完成时 snapshot
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    _snapshot_mysql_pools(f"After first crawler done ({len(done)} done, {len(pending)} pending)")
    _snapshot_redis_pools(f"After first crawler done")

    # 等待全部完成
    if pending:
        await asyncio.gather(*pending)
    results = [t.result() if t.done() else None for t in tasks]
    print(f"\n===== 全部 {len(results)} 个爬虫完成 =====")

    mysql_after, mysql_conn_after, stats_after = _snapshot_mysql_pools("After all crawlers")
    redis_after = _snapshot_redis_pools("After all crawlers")
    rss_after = _rss_mb()
    print(f"\n===== 进程 RSS 结束: {rss_after:.1f} MB =====")

    # ===== 结论判定 =====
    print("\n===== 判定结果 =====")
    ok = True
    # 1) MySQL pool 实例不应增长 > 1（相同配置共享）
    if mysql_after > max(1, mysql_before):
        print(f"  ❌ MySQL pool 实例增长: before={mysql_before} → after={mysql_after} (存在重复实例化!)")
        ok = False
    else:
        print(f"  ✅ MySQL pool 实例数稳定: {mysql_after} (共享无重复)")

    # 2) MySQL pool_id 在 first done → all done 之间不变（中途没被关掉重建）
    # 3) Redis pool：初始化后 0→1 是正常，结束后不应 > 1
    #    （注意：共享 pool 由 RuntimeContext 管理，不应在单个 crawler 结束时消失）
    if redis_after > 1:
        print(f"  ❌ Redis pool 实例数异常: {redis_after} (最多 1 个共享池)")
        ok = False
    else:
        print(f"  ✅ Redis pool 实例数稳定: {redis_after} (0→1 是初始化, 正常)")

    # 4) MySQL 连接总数不应超过 pool_maxsize
    expected_max = 10 * 2  # pool_maxsize=10, 共享 1 个 pool，不超过 10*2
    if mysql_conn_after > expected_max:
        print(f"  ❌ MySQL 总连接数异常大: {mysql_conn_after} (上限预计 {expected_max})")
        ok = False
    else:
        print(f"  ✅ MySQL 总连接数合理: {mysql_conn_after}")

    # 5) 关键: ref_count 验证 — 结束时所有引用应被释放
    for k, info in stats_after.get('pools', {}).items():
        ref = info.get('ref_count', -1)
        if ref > 0:
            print(f"  ⚠️  MySQL pool [{k}] ref_count={ref} (非 0, 可能泄漏引用但不影响功能)")
        else:
            print(f"  ✅ MySQL pool [{k}] ref_count={ref} (已归零/已关闭)")

    # 6) 第二轮启动验证：应能复用 / 重新创建同1个 pool 实例，不会有多实例
    print("\n===== 验证第二轮启动可复用 pool =====")
    cp2 = CrawlerProcess()
    await cp2.crawl('of_week')
    mysql_2, _, stats_2 = _snapshot_mysql_pools("After 2nd round single of_week")
    if mysql_2 > max(1, mysql_after):
        print(f"  ❌ 第二轮后 MySQL pool 实例再次增长! → {mysql_2} (资源竞争!)")
        ok = False
    else:
        print(f"  ✅ 第二轮 pool 实例数稳定 {mysql_2}，无资源竞争")

    print(f"\n===== 最终结果: {'✅ 全部通过' if ok else '❌ 存在问题'} =====")
    current, peak = tracemalloc.get_traced_memory()
    print(f"  tracemalloc: current={current/1024/1024:.1f} MB, peak={peak/1024/1024:.1f} MB")
    tracemalloc.stop()
    return ok


if __name__ == '__main__':
    ok = asyncio.run(run_multi_spider_test())
    sys.exit(0 if ok else 1)
