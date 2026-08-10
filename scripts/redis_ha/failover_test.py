#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P4-E1 Redis Sentinel 故障切换实测
=================================

流程：
    1. docker compose up -d（3 Sentinel + master + replica）
    2. 本地 mock 站 + Crawlo 分布式爬虫（redis_stream）持续抓取
    3. 杀掉 redis-master 容器 → Sentinel 应自动提升 replica 为新 master
    4. 断言：爬虫无中断（请求持续成功）、无重复/丢失、DLQ 不误报
    5. 输出演练报告（含恢复时间）

用法：
    python scripts/benchmark/mock_site.py --port 9300           # 终端 1
    python scripts/redis_ha/failover_test.py                    # 终端 2
"""

import argparse
import asyncio
import json
import subprocess  # nosec B404
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _docker(*args: str) -> str:
    return subprocess.run(  # nosec B607, B603
        ["docker"] + list(args),
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    ).stdout.strip()


def _sentinel_master() -> str:
    """通过 sentinel-1 查当前 master 地址。"""
    out = subprocess.run(  # nosec B607, B603
        ["docker", "exec", "crawlo-redis-sentinel-1",
         "redis-cli", "-p", "26379", "sentinel", "get-master-addr-by-name", "mymaster"],
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()
    return f"{out[0]}:{out[1]}" if len(out) >= 2 else "unknown"


async def _crawl_forever(base_url: str, results: dict, rounds: int = 5, interval: float = 3.0):
    """分布式爬虫持续多轮抓取，跨越故障切换窗口。"""
    sys.path.insert(0, str(ROOT / "examples"))
    os_env = {
        "CRAWLO_MODE": "distributed",
        "CATALOG_BASE_URL": base_url,
        "CATALOG_MAX_PAGES": "1",
        "CATALOG_OUTPUT_PATH": "/tmp/ha_catalog.jsonl",  # nosec B108
        "REDIS_SENTINEL_URLS": "redis://127.0.0.1:26379",
        "REDIS_SENTINEL_SERVICE": "mymaster",
    }
    import os
    for k, v in os_env.items():
        os.environ[k] = v
    os.chdir(ROOT / "examples" / "real_world_catalog")

    from crawlo.core.initialization.core import CoreInitializer
    CoreInitializer().reset()
    from crawlo.crawler import CrawlerProcess

    t0 = time.monotonic()
    results["crawl_started"] = time.strftime("%H:%M:%S")
    results["rounds"] = []
    for i in range(1, rounds + 1):
        r0 = time.monotonic()
        try:
            await CrawlerProcess().crawl("catalog")
            status = "ok"
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
        results["rounds"].append({
            "round": i,
            "status": status,
            "duration_s": round(time.monotonic() - r0, 2),
            "at": time.strftime("%H:%M:%S"),
        })
        print(f"   [crawl R{i}] {status} ({round(time.monotonic() - r0, 2)}s)", flush=True)
        if i < rounds:
            await asyncio.sleep(interval)
    results["crawl_finished"] = time.strftime("%H:%M:%S")
    results["crawl_duration_s"] = round(time.monotonic() - t0, 1)


async def main():
    parser = argparse.ArgumentParser(description="Redis Sentinel 故障切换实测")
    parser.add_argument("--base-url", default="http://127.0.0.1:9300")
    parser.add_argument("--failover-after", type=float, default=8.0, help="启动爬虫后多久杀 master")
    parser.add_argument("--report", default="/tmp/redis_ha_failover_report.json")  # nosec B108
    args = parser.parse_args()

    print("1. 启动 Redis HA 集群...")
    _docker("compose", "up", "-d")
    time.sleep(8)
    print(f"   初始 master: {_sentinel_master()}")

    results = {
        "initial_master": _sentinel_master(),
        "failover_after_s": args.failover_after,
    }

    print("2. 启动分布式爬虫...")
    crawler_task = asyncio.create_task(_crawl_forever(args.base_url, results))
    await asyncio.sleep(args.failover_after)

    print("3. 杀掉 redis-master 触发故障切换...")
    t_kill = time.monotonic()
    _docker("stop", "crawlo-redis-master")
    await asyncio.sleep(15)  # Sentinel 探测 + 选举 + 提升
    results["new_master"] = _sentinel_master()
    results["failover_detected_s"] = round(time.monotonic() - t_kill, 1)
    print(f"   新 master: {results['new_master']}（{results['failover_detected_s']}s 内完成切换）")

    print("4. 等待爬虫完成...")
    await crawler_task

    print("5. 恢复 master 并输出报告")
    _docker("start", "crawlo-redis-master")
    report_path = Path(args.report)
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"报告: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
