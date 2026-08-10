#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P4-E2 长驻稳定性压力测试
=======================

周期性运行 real_world_catalog 示例爬虫（对本地 mock 站），收集：
    - RSS 内存（进程级）
    - 事件循环延迟 P50/P95/P99（EventloopLagProbe 或内置探针）
    - ResourceScope 对象计数（Crawler/Pipeline/Downloader/Filter 泄漏斜率）
    - Redis 连接池大小、文件描述符数量

用法：
    python scripts/stress_run.py --rounds 50 --interval 10 --report /tmp/stress.json

建议正式执行（24h）：--rounds 8640 --interval 10（约 24 小时）。
验收阈值（示例值，可按部署机器调整）：
    - RSS 增长 < 200 MB
    - 对象泄漏斜率 < 0.05 / 轮
    - 事件循环延迟 P99 < 100 ms
"""

import argparse
import asyncio
import gc
import json
import os
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "real_world_catalog"


def _rss_mb() -> float:
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024.0 / 1024.0
    except ImportError:
        ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return ru / 1024.0 if sys.platform.startswith("linux") else ru / 1024.0 / 1024.0


def _fd_count() -> int:
    return len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else -1


def _redis_conns() -> int:
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=2)
        return int(r.info("clients").get("connected_clients", -1))
    except Exception:
        return -1


async def _run_round(round_no: int, base_url: str) -> dict:
    sys.path.insert(0, str(ROOT / "examples"))
    os.environ["CATALOG_BASE_URL"] = base_url
    os.environ["CATALOG_MAX_PAGES"] = "2"
    os.environ["CATALOG_OUTPUT_PATH"] = "/tmp/stress_catalog.jsonl"  # nosec B108
    os.chdir(EXAMPLE_DIR)

    from crawlo.core.initialization.core import CoreInitializer
    CoreInitializer().reset()
    from crawlo.crawler import CrawlerProcess

    t0 = time.monotonic()
    await CrawlerProcess().crawl("catalog")
    return {"round": round_no, "duration_s": round(time.monotonic() - t0, 2)}


async def _eventloop_lag_estimate() -> dict:
    """用两次时钟对比粗略估计事件循环延迟（无探针时兜底）。"""
    delays = []

    async def _probe():
        for _ in range(20):
            t0 = time.perf_counter()
            await asyncio.sleep(0)
            delays.append((time.perf_counter() - t0) * 1000)

    await _probe()
    delays.sort()
    p = lambda q: delays[min(int(q * len(delays)), len(delays) - 1)]
    return {"p50_ms": round(p(0.5), 3), "p95_ms": round(p(0.95), 3), "p99_ms": round(p(0.99), 3)}


async def main():
    parser = argparse.ArgumentParser(description="Crawlo 长驻稳定性压力测试")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--interval", type=float, default=5.0, help="轮间间隔（秒）")
    parser.add_argument("--warmup", type=int, default=2, help="预热轮数（不计入斜率）")
    parser.add_argument("--base-url", default="http://127.0.0.1:9200")
    parser.add_argument("--report", default="/tmp/crawlo_stress_report.json")  # nosec B108
    args = parser.parse_args()

    from crawlo.core.resource_scope import ResourceScope

    scope = ResourceScope(
        mode="scheduler",
        name="stress-24h",
        watch_types={
            "Crawler", "CrawlerProcess", "PipelineManager",
            "AioHttpDownloader", "AioRedisFilter",
        },
        iteration_warn_slope={"Crawler": 0.05},
    )
    # 预热：先跑几轮，让框架/连接池进入稳态后再设基线
    for i in range(1, args.warmup + 1):
        await _run_round(i, args.base_url)
        gc.collect()
        print(f"[WARMUP {i}] rss={_rss_mb():.1f}MB", flush=True)
    scope.counter.set_baseline()
    gc.collect()

    report = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rounds": args.rounds,
        "interval_s": args.interval,
        "rss_mb_start": round(_rss_mb(), 1),
        "warmup_rounds": args.warmup,
        "snapshots": [],
        "leak_slopes": {},
    }

    for i in range(1, args.rounds + 1):
        round_info = await _run_round(i, args.base_url)
        gc.collect()
        delta = scope.counter.delta()
        report["snapshots"].append({
            "round": i,
            "rss_mb": round(_rss_mb(), 1),
            "fd_count": _fd_count(),
            "redis_clients": _redis_conns(),
            "object_delta": delta,
            **round_info,
        })
        await scope.on_iteration_end(f"R{i}")
        print(
            f"[R{i:>4}] rss={report['snapshots'][-1]['rss_mb']:.1f}MB "
            f"redis_clients={report['snapshots'][-1]['redis_clients']} "
            f"delta={delta} dur={round_info['duration_s']}s",
            flush=True,
        )
        if i < args.rounds:
            await asyncio.sleep(args.interval)

    report["leak_slopes"] = scope.counter.linear_slopes()
    report["rss_mb_end"] = round(_rss_mb(), 1)
    report["rss_growth_mb"] = round(report["rss_mb_end"] - report["rss_mb_start"], 1)
    report["eventloop_lag"] = await _eventloop_lag_estimate()

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n报告已写入: {args.report}")
    print(f"RSS 增长: {report['rss_growth_mb']} MB")
    print(f"泄漏斜率: {report['leak_slopes']}")
    print(f"事件循环延迟: {report['eventloop_lag']}")
    await scope.close()


if __name__ == "__main__":
    asyncio.run(main())
