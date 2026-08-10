#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
real_world_catalog 启动入口

用法：
    python run.py                        # 单机模式（memory 队列）
    python run.py --distributed          # 分布式模式（redis_stream + 多 Worker 协作）
    python run.py --mode standalone      # 等价于默认

分布式模式需要本地 Redis（默认 127.0.0.1:6379），可开多个终端同时执行本脚本
组成 Worker 集群；关闭时由 Leader 协调广播退出。
"""

import argparse
import asyncio
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler import CrawlerProcess


def main():
    parser = argparse.ArgumentParser(description="real_world_catalog 示例入口")
    parser.add_argument("--distributed", action="store_true", help="分布式模式")
    parser.add_argument("--mode", choices=["standalone", "distributed"], default=None)
    args = parser.parse_args()

    if args.distributed or args.mode == "distributed":
        os.environ["CRAWLO_MODE"] = "distributed"
        print("▶ 分布式模式（QUEUE_TYPE=redis_stream）")
    else:
        os.environ["CRAWLO_MODE"] = "standalone"
        print("▶ 单机模式（QUEUE_TYPE=memory）")

    process = CrawlerProcess()
    try:
        asyncio.run(process.crawl("catalog"))
    except KeyboardInterrupt:
        print("\n收到中断信号，已停止")
        sys.exit(130)
    except Exception as exc:
        print(f"运行失败: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
