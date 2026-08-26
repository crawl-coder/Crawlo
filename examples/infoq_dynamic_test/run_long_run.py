#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
InfoQ 动态渲染长时运行测试入口
==============================
动态场景（列表/详情全浏览器渲染）长时间运行稳定性测试。

用法：
    # 5 分钟冒烟
    RUN_MINUTES=5 python run_long_run.py

    # 30 分钟标准长跑，详情上限 200
    RUN_MINUTES=30 MAX_DETAILS=200 python run_long_run.py

    # 数小时挂机（建议配合 nohup / tmux）
    RUN_MINUTES=240 python run_long_run.py

环境变量：
    RUN_MINUTES       运行时长上限（默认 30）
    LIST_INTERVAL     列表刷新最小间隔秒（默认 60）
    MAX_DETAILS       详情页总数安全阀（0=不限）
    DYNAMIC_BACKEND   动态下载器：cloakbrowser（默认）| playwright
"""
import os
import sys
import asyncio
from pathlib import Path

# 关键：优先使用仓库本地源码而非 pip 安装版——
# examples 目录下直接 import crawlo 会解析到 site-packages 的发布版，
# 两者的 DynamicRenderMiddleware 行为不同（旧版零配置即打 protocol 标记）。
_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root in sys.path:
    sys.path.remove(_repo_root)
sys.path.insert(0, _repo_root)

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import crawlo  # noqa: E402  确认解析到本地源码
assert crawlo.__file__.startswith(_repo_root), \
    f"import 到了非本地 crawlo: {crawlo.__file__}"

from crawlo.crawler import CrawlerProcess  # noqa: E402


def main():
    run_minutes = os.environ.get('RUN_MINUTES', '30')
    backend = os.environ.get('DYNAMIC_BACKEND', 'cloakbrowser')

    print("=" * 60)
    print(f"InfoQ 动态渲染长跑测试 | RUN_MINUTES={run_minutes} "
          f"| backend={backend}")
    print(f"crawlo 源码: {crawlo.__file__}")
    print("=" * 60)

    settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': backend,
        'HYBRID_DYNAMIC_DOMAINS': ['www.infoq.cn'],
        'PLAYWRIGHT_REAL_CHROME': True,          # backend=playwright 时复用系统 Chrome
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        # 长跑礼貌性限速
        'CONCURRENCY': 2,
        'DOWNLOAD_DELAY': 2.0,
        'ROBOTSTXT_OBEY': False,
        'RETRY_TIMES': 2,
        'LOG_LEVEL': 'INFO',
        # 长跑不刷屏：去掉 ConsolePipeline，改为 JSONL 落盘
        'PIPELINES': {'infoq_dynamic_test.pipelines.JsonlPipeline': 100},
    }

    try:
        asyncio.run(CrawlerProcess().crawl('infoq_longrun_spider',
                                           settings=settings))
    except KeyboardInterrupt:
        print("\n[runner] 手动中断")
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
