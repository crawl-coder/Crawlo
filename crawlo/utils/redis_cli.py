#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CLI 工具统一 Redis 地址解析（B5）。

四级回退（CLI 工具无 crawl 上下文，settings 由调用方显式传入）：
1. 命令行 ``--redis-url <url>``；
2. ``CRAWLO_REDIS_URL`` 环境变量（Crawlo 专用，推荐项目/容器使用）；
3. ``REDIS_URL`` 环境变量（通用约定，与 cluster.py 历史行为兼容）；
4. settings 字典中 ``REDIS_URL``（仅在有 crawl 上下文时传入，如 run.py）；
5. 默认值 ``redis://127.0.0.1:6379/0``。

用法::

    # dead_letter.py（纯 CLI，无 settings）
    redis_url = resolve_redis_url(args)

    # run.py（有 crawl 上下文）
    redis_url = resolve_redis_url(args=[], settings=crawler.settings)

    # cluster.py
    redis_url = resolve_redis_url(args)
"""
from typing import List, Optional

DEFAULT_REDIS_URL = "redis://127.0.0.1:6379/0"


def _parse_flag(args: List[str], flag: str) -> Optional[str]:
    """从 CLI 参数列表中提取 ``--flag value``，返回 value 或 None。"""
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args):
            return args[i + 1]
    return None


def resolve_redis_url(
    args: Optional[List[str]] = None,
    cli_flag: str = "--redis-url",
    settings: Optional[dict] = None,
) -> str:
    """四级回退解析 Redis URL。"""
    # 1. 命令行参数
    url = _parse_flag(args or [], cli_flag)
    if url:
        return url

    # 2. Crawlo 专用环境变量（推荐用于项目/容器场景）
    import os
    url = os.environ.get("CRAWLO_REDIS_URL")
    if url:
        return url

    # 3. 通用环境变量（兼容历史 cluster.py 约定）
    url = os.environ.get("REDIS_URL")
    if url:
        return url

    # 4. settings 字典（有 crawl 上下文时由调用方传入）
    if settings is not None:
        url = settings.get("REDIS_URL")
        if url:
            return url

    # 5. 默认值
    return DEFAULT_REDIS_URL
