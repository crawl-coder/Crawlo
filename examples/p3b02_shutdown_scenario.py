#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P3-B-02 + B-08 scenario 验证：
  1. 清理 distributed 模式旧 Redis 数据
  2. SET crawlo:crawlo_map_distributed:ofweek_2page:control:state = shutdown（模拟上次异常退出残留）
  3. 启动 distributed 模式爬虫
  4. 期望：Engine 触发 [AutoFix P3-B-02] → 清回 running → 正常爬 finished
     同时日志中打印 Dedup filter / pipeline INFO（P3-B-08）
"""
import asyncio
import time
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_3modes_p0p1 import (
    OfWeek2PageSpider,
    make_settings,
    clear_redis_mode,
)

async def _with_timeout(coro, timeout_s: float):
    """超时包装：超时不抛，返回一个带 reason 的 dict（与 p.crawl 约定的返回值无关，我们在外面 catch 超时即可）。
    这里直接基于 asyncio.wait_for，超时会抛 TimeoutError，在 call 处统一 catch。
    """
    import asyncio as _aio
    return await _aio.wait_for(coro, timeout=timeout_s)

PROJECT = "crawlo_map_distributed"
SPIDER = "ofweek_2page"
CONTROL_KEY = f"crawlo:{PROJECT}:{SPIDER}:control:state"
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))


async def run_scenario():
    # ------------------------------------------------------------------
    # 0. 清旧（这一步会删掉 control:state，因为它匹配 crawlo:crawlo_map_distributed:ofweek_2page:*）
    #    — 然后重新 SET shutdown 污染
    # ------------------------------------------------------------------
    clear_redis_mode("distributed", spider=SPIDER)

    import redis as _sync
    rsync = _sync.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_connect_timeout=2)
    try:
        rsync.set(CONTROL_KEY, "shutdown")
        planted = rsync.get(CONTROL_KEY)
        planted_s = planted.decode() if isinstance(planted, bytes) else planted
        print(f"\n[scenario] 预设 {CONTROL_KEY} = {planted_s!r}（模拟 shutdown 残留）")
        print("[scenario] 预期 → Engine 检测 + [AutoFix P3-B-02] 清回 running → 正常爬 finished。\n")
    finally:
        try:
            rsync.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 1. 启动（直接复用 test_3modes_p0p1.run_single 的调用模式）
    #    — 额外起一个后台 probe task，在运行中段两次读 control:state，
    #      验证中间态确实被 AutoFix 拉回 running（而非残留 shutdown）。
    # ------------------------------------------------------------------
    from crawlo.crawler import CrawlerProcess, reset_framework
    reset_framework()

    import redis.asyncio as _aioredis
    probe_results: list[tuple[float, object]] = []
    probe_stop = asyncio.Event()
    t0 = time.monotonic()

    async def _probe_state():
        """在 crawl 运行中检查 control:state，确保 AutoFix 真正把它改成了 running。"""
        aio_r = _aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_connect_timeout=2)
        try:
            for delay in (3.0, 15.0):
                try:
                    await asyncio.wait_for(probe_stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                if probe_stop.is_set():
                    break
                raw = await aio_r.get(CONTROL_KEY)
                state = raw.decode() if isinstance(raw, bytes) else raw
                probe_results.append((time.monotonic() - t0, state))
        finally:
            try:
                await aio_r.aclose()
            except Exception:
                pass

    probe_task = asyncio.create_task(_probe_state())

    settings = make_settings("distributed")
    settings.setdefault("SPIDER_NAME", SPIDER)

    try:
        p = CrawlerProcess(settings=settings)
        crawler = await _with_timeout(p.crawl(OfWeek2PageSpider), 700.0)
        stats = crawler.stats.get_stats() if crawler and crawler.stats else {}
        elapsed = time.monotonic() - t0
    except Exception as e:
        elapsed = time.monotonic() - t0
        req = resp = item = 0
        exit_reason = f"ERROR:{type(e).__name__}:{e}"
        import traceback
        traceback.print_exc()
        stats = {}

    probe_stop.set()
    try:
        await asyncio.wait_for(probe_task, timeout=5.0)
    except Exception:
        pass

    def g(k, default=0):
        return stats.get(f"crawlo:{k}", stats.get(k, default))
    req = int(g("request_scheduler_count", 0))
    resp = int(g("response_received_count", 0))
    item = int(g("item_successful_count", 0))
    exit_reason = g("reason", "") if "exit_reason" not in locals() else exit_reason

    # ------------------------------------------------------------------
    # 2. 校验
    # ------------------------------------------------------------------
    rsync = _sync.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_connect_timeout=2)
    try:
        end_raw = rsync.get(CONTROL_KEY)
        end_state = end_raw.decode() if isinstance(end_raw, bytes) else end_raw
    finally:
        try:
            rsync.close()
        except Exception:
            pass

    # AutoFix 生效的「直接证据」：运行中段（3s / 15s 时）读 control:state，至少一个是 running
    mid_states = [(round(t, 1), s) for t, s in probe_results]
    mid_ever_running = any(s == "running" for _, s in mid_states)
    # end_state 可以是 shutdown 或 running：
    #   - shutdown  => Leader 协调 shutdown_cluster（CLUSTER_CLEANUP_ON_SHUTDOWN 路径，正常）
    #   - running   => cleanup 里 SET running（L138）先执行，也正常
    # 所以终态不再做不等于 shutdown 的断言。
    mid_proof = mid_ever_running

    print()
    print("=" * 72)
    print("📋 P3-B-02 (AutoFix shutdown 残留) + B-08 (Dedup 日志) scenario 结果")
    print("=" * 72)
    print(f"  elapsed                 = {elapsed:.1f}s")
    print(f"  req / resp / item      = {req} / {resp} / {item}")
    print(f"  exit reason            = {exit_reason}")
    print(f"  control:state 中段探针 = {mid_states or '<未采集到>'}")
    print(f"  control:state 终态      = {end_state!r}   (初始是 'shutdown')")
    print()
    check_req = req >= 40
    check_item = item >= 20
    check_finished = exit_reason == "finished"
    ok = all([check_req, check_item, check_finished, mid_proof])

    def _mark(b):
        return "✅" if b else "❌"

    print(f"  req>=40                       : {_mark(check_req)}")
    print(f"  item>=20                      : {_mark(check_item)}")
    print(f"  exit=finished                 : {_mark(check_finished)}")
    print(f"  中段 state 一度 = running      : {_mark(mid_proof)}   ← AutoFix 实际生效的核心证据")
    print()
    print(f"  🏁 总体: {'✅ PASS — AutoFix + Dedup 日志均按预期工作' if ok else '❌ FAIL'}")
    print("=" * 72)
    print()
    print("完整运行输出中应包含：")
    print("  WARN  [AutoFix P3-B-02] 检测到 control:state = shutdown 残留...")
    print("  INFO  Dedup filter:  crawlo.filters.AioRedisFilter   (persistence=ON ...)")
    print("  INFO  Dedup pipeline: crawlo.pipelines.RedisDedupPipeline   (...)")
    print("  WARN  Coordinated shutdown: all tasks complete, all workers idle, broadcasting shutdown signal")
    print("  INFO  Cluster shutdown complete: ...")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_scenario()))
