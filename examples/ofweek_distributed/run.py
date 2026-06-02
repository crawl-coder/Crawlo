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
        asyncio.run(process.crawl('of_week_distributed'))

    except KeyboardInterrupt:
        print("\n收到中断信号，已停止")
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



if __name__ == '__main__':
    main()
