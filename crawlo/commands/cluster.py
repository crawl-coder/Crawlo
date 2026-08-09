#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
命令行入口：crawlo cluster，分布式集群管理（P3-B-02 方案 C 兜底）。

用法：
    crawlo cluster state   <project> <spider>                查看当前 control:state
    crawlo cluster reset   <project> <spider>                重置 control:state→running + 清 leader 锁（B-02 兜底：0 Worker 残留 shutdown 时用）
    crawlo cluster pause   <project> <spider>                暂停所有 Worker（持久化 SET + Pub/Sub）
    crawlo cluster resume  <project> <spider>                恢复所有 Worker
    crawlo cluster shutdown <project> <spider> [--no-cleanup] 通知所有 Worker 停止（可选不清 dedup/registry）

默认连接 redis://127.0.0.1:6379/0，如需自定义用环境变量 REDIS_URL 或 --redis-url：
    crawlo cluster reset map_project map_spider --redis-url redis://user:pass@host:6379/2
"""
import os
import sys
import asyncio

from crawlo.logging import get_logger

logger = get_logger(__name__)


def main(args):
    if len(args) < 2:
        _print_usage()
        return

    action = args[1]
    if action in ("-h", "--help", "help"):
        _print_usage()
        return

    if len(args) < 4:
        print("错误：缺少 <project> / <spider> 参数")
        _print_usage()
        sys.exit(1)

    project = args[2]
    spider = args[3]
    redis_url = _extract_redis_url(args)

    if action == "state":
        asyncio.run(_show_state(project, spider, redis_url))
    elif action == "reset":
        asyncio.run(_reset(project, spider, redis_url))
    elif action == "pause":
        asyncio.run(_pause(project, spider, redis_url))
    elif action == "resume":
        asyncio.run(_resume(project, spider, redis_url))
    elif action == "shutdown":
        no_cleanup = "--no-cleanup" in args
        asyncio.run(_shutdown(project, spider, redis_url, cleanup=not no_cleanup))
    else:
        print(f"未知 action: {action}")
        _print_usage()
        sys.exit(1)


def _print_usage():
    print("crawlo cluster — 分布式集群管理（P3-B-02）")
    print()
    print("用法:")
    print("  crawlo cluster state    <project> <spider>                  查看 control:state + registry 摘要")
    print("  crawlo cluster reset    <project> <spider>                  清 control:state + leader（B-02 兜底命令）")
    print("  crawlo cluster pause    <project> <spider>                  持久化暂停所有 Worker")
    print("  crawlo cluster resume   <project> <spider>                  恢复所有 Worker")
    print("  crawlo cluster shutdown <project> <spider> [--no-cleanup]   通知集群结束（默认清运行数据）")
    print()
    print("公共选项（任一位置可加）:")
    print("  --redis-url redis://host:port/db                            目标 Redis（默认环境变量 REDIS_URL 或 127.0.0.1:6379/0）")


def _extract_redis_url(args):
    for i, arg in enumerate(args):
        if arg == "--redis-url" and i + 1 < len(args):
            return args[i + 1]
    return os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")


# ----------------------------------------------------------------------
# 实际动作（都走 aioredis，避免依赖完整 Crawlo settings）
# ----------------------------------------------------------------------

async def _show_state(project, spider, redis_url):
    ns = f"crawlo:{project}:{spider}"
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
    except Exception as e:
        print(f"[cluster state] 无法创建 Redis 客户端: {e}")
        sys.exit(1)

    control_key = f"{ns}:control:state"
    leader_key = f"{ns}:cluster:leader"
    workers_key = f"crawlo:{ns}:registry:workers"
    heartbeats_key = f"crawlo:{ns}:registry:heartbeats"

    # ---- 控制状态 ----
    state = await r.get(control_key)
    if isinstance(state, bytes):
        state = state.decode("utf-8")
    leader = await r.get(leader_key)
    if isinstance(leader, bytes):
        leader = leader.decode("utf-8")[:32] + ("..." if len(leader) > 32 else "")
    alive_cnt = await r.zcard(heartbeats_key)
    workers_cnt = await r.hlen(workers_key)

    stream_main = f"{ns}:stream:tasks"
    stream_high = f"{ns}:stream:tasks_high"
    stream_failed = f"{ns}:stream:failed"
    xlen_main = await r.xlen(stream_main)
    xlen_high = await r.xlen(stream_high)
    xlen_dead = await r.xlen(stream_failed)

    print(f"[cluster] project={project} spider={spider} namespace={ns}")
    print(f"  control:state      = {state or '<running (no key)>'}")
    print(f"  cluster:leader     = {leader or '<none>'}")
    print(f"  registry workers   = {workers_cnt} total / {alive_cnt} alive (heartbeats)")
    print(f"  stream xlen        = main:{xlen_main}  high:{xlen_high}  dead_letter:{xlen_dead}")

    # ---- XPENDING 概览（仅在有消息时执行，避免 INFO 级报错）----
    try:
        for sname, skey in (("main", stream_main), ("high", stream_high)):
            if xlen_main or sname != "main":
                pending = await r.xpending(skey)
                if pending and pending.get("pending"):
                    print(f"  pending[{sname}] total={pending['pending']}  consumers={list(pending.get('consumers', {}).keys())[:3]}")
    except Exception as e:
        logger.debug(f"XPENDING overview failed: {e}")

    await r.aclose()


async def _reset(project, spider, redis_url):
    """B-02 方案 C 兜底：强制清理 control:state + cluster:leader 以及可选 stream:failed 清零"""
    ns = f"crawlo:{project}:{spider}"
    print(f"[cluster reset] namespace={ns} 即将执行：")
    print(f"  - SET  {ns}:control:state = running   （替代 shutdown/paused 残留）")
    print(f"  - DEL  {ns}:cluster:leader             （清孤立 Leader 锁）")
    print()
    resp = input("确认执行? [y/N] ").strip().lower()
    if resp not in ("y", "yes"):
        print("已取消。")
        return

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
    except Exception as e:
        print(f"[cluster reset] 无法创建 Redis 客户端: {e}")
        sys.exit(1)

    try:
        control_key = f"{ns}:control:state"
        leader_key = f"{ns}:cluster:leader"
        await r.set(control_key, "running")
        await r.delete(leader_key)
        print("  ✓ control:state → running")
        print("  ✓ cluster:leader deleted")

        # 额外：如果 registry:heartbeats 全 dead（> 1 天老）也提示
        heartbeats_key = f"crawlo:{ns}:registry:heartbeats"
        hb_cnt = await r.zcard(heartbeats_key)
        if hb_cnt == 0:
            print("  ℹ registry:heartbeats = 0，确认集群当前无活跃 Worker，reset 安全。")
        else:
            print(f"  ⚠ registry:heartbeats 仍有 {hb_cnt} 条记录。若 Worker 还在运行，请先停止它们。")
    finally:
        try:
            await r.aclose()
        except Exception as e:
            logger.debug(f"Redis client close failed: {e}")
    print()
    print("reset 完成：Worker 下次启动将正常进入 running 状态。")


async def _pause(project, spider, redis_url):
    print(f"[cluster pause] {project}/{spider} ...")
    try:
        from crawlo.cluster.config import DynamicConfig
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
        dc = DynamicConfig(r, messenger=None, namespace=f"crawlo:{project}:{spider}", enabled=False)
        await dc.pause_spider()
        print("✓ pause 成功：SET control:state = paused + PUBLISH control:pause 发出")
        await r.aclose()
    except Exception as e:
        print(f"pause 失败: {e}")
        sys.exit(1)


async def _resume(project, spider, redis_url):
    print(f"[cluster resume] {project}/{spider} ...")
    try:
        from crawlo.cluster.config import DynamicConfig
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
        dc = DynamicConfig(r, messenger=None, namespace=f"crawlo:{project}:{spider}", enabled=False)
        await dc.resume_spider()
        print("✓ resume 成功：SET control:state = running + PUBLISH control:resume 发出")
        await r.aclose()
    except Exception as e:
        print(f"resume 失败: {e}")
        sys.exit(1)


async def _shutdown(project, spider, redis_url, cleanup=True):
    print(f"[cluster shutdown] {project}/{spider}  cleanup={cleanup} ...")
    try:
        from crawlo.cluster.config import DynamicConfig
        import redis.asyncio as aioredis
        r = aioredis.from_url(redis_url, socket_connect_timeout=3)
        dc = DynamicConfig(r, messenger=None, namespace=f"crawlo:{project}:{spider}", enabled=False)
        await dc.shutdown_cluster(cleanup=cleanup)
        print("✓ shutdown 成功：SET control:state = shutdown + PUBLISH control:shutdown 发出"
              + ("（附带 cleanup 运行数据）" if cleanup else "（保留运行数据）"))
        await r.aclose()
    except Exception as e:
        print(f"shutdown 失败: {e}")
        sys.exit(1)
