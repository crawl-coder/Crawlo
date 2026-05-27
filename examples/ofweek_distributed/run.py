#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ofweek_distributed — 分布式爬虫示例

使用 Crawlo 新版分布式功能（Redis Streams + Consumer Groups + ACK）：
- QUEUE_TYPE = redis_stream（Consumer Groups + XACK 确认机制）
- 自动 Worker 注册与心跳
- 崩溃任务自动回收（XCLAIM/XAUTOCLAIM）
- 集群状态监控

运行方式（多 Worker）：
    # 终端 1（第一个 Worker，创建 Consumer Group）
    cd examples/ofweek_distributed
    python run.py

    # 终端 2+（更多 Worker，自动加入 Consumer Group）
    python run.py
"""
import os
import sys
import asyncio

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler import CrawlerProcess


def main():
    """运行分布式爬虫"""
    try:
        process = CrawlerProcess()
        crawler = asyncio.run(process.crawl('of_week_distributed'))

        # 显示集群运行摘要（新版分布式功能）
        _print_cluster_status(crawler)

    except KeyboardInterrupt:
        print("\n收到中断信号，已停止")
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _print_cluster_status(crawler):
    """打印集群状态汇总"""
    engine = getattr(crawler, '_engine', None)
    if not engine or not getattr(engine, '_cluster_worker_id', None):
        return

    try:
        print("\n" + "=" * 55)
        print("  Crawlo 分布式集群 — 运行摘要")
        print("=" * 55)
        print(f"  Worker:      {engine._cluster_worker_id}")

        if engine._cluster_monitor:
            s = asyncio.run(engine._cluster_monitor.status())
            print(f"  活跃节点:     {s['workers']['active']}/{s['workers']['total']}")
            print(f"  队列 Pending: {s['queue']['pending']}")
            print(f"  队列处理中:   {s['queue']['processing']}")
            print(f"  完成:         {s['progress']['completed']}")
            print(f"  失败:         {s['progress']['failed']}")
            print(f"  速率:         {s['progress']['items_per_sec']}/s")
            dead_total = s['dead_letter'].get('total', 0)
            if dead_total > 0:
                print(f"  死信队列:     {dead_total}")

        print("=" * 55)
    except Exception as e:
        from crawlo.logging import get_logger
        get_logger(__name__).debug(f"Cluster status: {e}")


if __name__ == '__main__':
    main()
