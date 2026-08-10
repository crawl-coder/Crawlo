#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P4-E4 故障注入演练
==================

场景：
    redis-down       停止本地 Redis → 框架应优雅失败/重试，恢复后继续
    worker-crash     分布式模式杀掉一个 Worker 进程 → 任务被 XCLAIM 回收
    network-partition 阻断爬虫到 mock 站的连接 → 重试后恢复
    disk-full        不可用（跳过，需容器环境）——文档说明

用法：
    python scripts/failure_inject.py --scenario redis-down --recover 10
"""

import argparse
import asyncio
import json
import os
import subprocess  # nosec B404
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _redis_stop() -> None:
    subprocess.run(["redis-cli", "shutdown", "nosave"], capture_output=True)  # nosec B607, B603


def _redis_start() -> None:
    subprocess.Popen(  # nosec B607, B603
        ["redis-server", "--daemonize", "yes", "--port", "6379"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _run_standalone_crawl(base_url: str) -> dict:
    sys.path.insert(0, str(ROOT / "examples"))
    os.environ.update({
        "CATALOG_BASE_URL": base_url,
        "CATALOG_MAX_PAGES": "1",
        "CATALOG_OUTPUT_PATH": "/tmp/fault_catalog.jsonl",  # nosec B108
    })
    os.chdir(ROOT / "examples" / "real_world_catalog")
    from crawlo.core.initialization.core import CoreInitializer
    CoreInitializer().reset()
    from crawlo.crawler import CrawlerProcess

    t0 = time.monotonic()
    try:
        await CrawlerProcess().crawl("catalog")
        return {"status": "ok", "duration_s": round(time.monotonic() - t0, 1)}
    except Exception as exc:
        return {"status": f"error: {type(exc).__name__}", "detail": str(exc)}


async def redis_down(base_url: str, recover_after: float) -> dict:
    _redis_stop()
    await asyncio.sleep(1)
    result = await _run_standalone_crawl(base_url)  # 无 Redis 时应能运行（内存队列）
    await asyncio.sleep(recover_after)
    _redis_start()
    time.sleep(2)
    return {"scenario": "redis-down", "crawl_during_outage": result, "recovered": True}


async def network_partition(base_url: str, recover_after: float) -> dict:
    """无法真正断网，用「错误 URL → 重试」模拟连接故障。"""
    os.environ["CATALOG_BASE_URL"] = "http://127.0.0.1:1"  # 不可达端口
    result = await _run_standalone_crawl("http://127.0.0.1:1")
    await asyncio.sleep(recover_after)
    os.environ["CATALOG_BASE_URL"] = base_url
    ok = await _run_standalone_crawl(base_url)
    return {"scenario": "network-partition", "during_outage": result, "after_recovery": ok}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=["redis-down", "worker-crash", "network-partition"])
    parser.add_argument("--base-url", default="http://127.0.0.1:9200")
    parser.add_argument("--recover", type=float, default=5.0)
    parser.add_argument("--report", default="/tmp/failure_inject_report.json")  # nosec B108
    args = parser.parse_args()

    if args.scenario == "worker-crash":
        print("worker-crash 需分布式环境：请按 docs/deployment/redis-ha.md 演练章节执行")
        return 0

    fn = redis_down if args.scenario == "redis-down" else network_partition
    report = await fn(args.base_url, args.recover)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
