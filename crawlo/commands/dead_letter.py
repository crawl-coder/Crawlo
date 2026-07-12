#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
命令行入口：crawlo dead-letter，死信队列管理

用法：
    crawlo dead-letter list <project> <spider>    查看死信
    crawlo dead-letter retry <project> <spider>   重新入队(--count N)
    crawlo dead-letter stats <project> <spider>   查看统计
"""
import sys
import asyncio
from crawlo.logging import get_logger

logger = get_logger(__name__)


def main(args):
    if len(args) < 2:
        _print_usage()
        return

    action = args[1]
    project = args[2] if len(args) > 2 else "default"
    spider = args[3] if len(args) > 3 else "default"

    if action == "list":
        asyncio.run(_list_dead_letters(project, spider, args))
    elif action in ("retry", "replay"):
        count = 100
        for i, arg in enumerate(args):
            if arg == "--count" and i + 1 < len(args):
                count = int(args[i + 1])
        asyncio.run(_retry_dead_letters(project, spider, count))
    elif action == "stats":
        asyncio.run(_show_stats(project, spider))
    else:
        _print_usage()


def _print_usage():
    print("crawlo dead-letter — 死信队列管理")
    print()
    print("用法:")
    print("  crawlo dead-letter list <project> <spider>   查看死信")
    print("  crawlo dead-letter retry <project> <spider>  重新入队 (--count N)")
    print("  crawlo dead-letter stats <project> <spider>  查看统计")


async def _list_dead_letters(project, spider, args):
    """查看死信内容"""
    limit = 20
    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://127.0.0.1:6379/0")

        key = f"crawlo:{project}:{spider}:stream:failed"
        length = await r.xlen(key)

        if length == 0:
            print(f"死信队列为空: {key}")
            await r.aclose()
            return

        msgs = await r.xrevrange(key, count=limit)
        print(f"死信队列: {key} (共 {length} 条，显示最近 {len(msgs)} 条)")
        print("-" * 60)

        for msg_id, fields in msgs:
            print(f"\n[消息 {msg_id.decode()[:16]}...]")
            for k, v in fields.items():
                k_str = k.decode() if isinstance(k, bytes) else k
                v_str = v.decode() if isinstance(v, bytes) else v
                if k_str == "data":
                    v_str = v_str[:200] + (f" ... ({len(v_str)} chars)" if len(v_str) > 200 else "")
                if k_str in ("dead_reason", "retry_count", "dead_at"):
                    print(f"  {k_str}: {v_str}")

        await r.aclose()
    except Exception as e:
        print(f"连接 Redis 失败: {e}")
        sys.exit(1)


async def _retry_dead_letters(project, spider, count):
    """重新入队死信"""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://127.0.0.1:6379/0")

        dead_key = f"crawlo:{project}:{spider}:stream:failed"
        stream_key = f"crawlo:{project}:{spider}:stream:tasks"

        msgs = await r.xrevrange(dead_key, count=count)
        if not msgs:
            print("死信队列为空")
            await r.aclose()
            return

        retried = 0
        for msg_id, fields in msgs:
            new_fields = {k: v for k, v in fields.items()
                          if k not in (b"retry_count", b"dead_at", b"dead_reason",
                                       b"original_message_id")}
            new_fields[b"retry_count"] = b"0"
            await r.xadd(stream_key, new_fields, maxlen=100000, approximate=True)
            await r.xdel(dead_key, msg_id)
            retried += 1

        print(f"重新入队 {retried}/{len(msgs)} 条死信到 {stream_key}")
        remaining = await r.xlen(dead_key)
        if remaining > 0:
            print(f"剩余 {remaining} 条死信未处理")

        await r.aclose()
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)


async def _show_stats(project, spider):
    """显示死信统计"""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://127.0.0.1:6379/0")

        dead_key = f"crawlo:{project}:{spider}:stream:failed"
        stream_key = f"crawlo:{project}:{spider}:stream:tasks"

        dead_count = await r.xlen(dead_key)
        task_count = await r.xlen(stream_key)
        pending = await r.xpending(stream_key, f"crawlo:{project}:{spider}:group:workers")

        print(f"项目: {project}/{spider}")
        print(f"待处理: {task_count}")
        print(f"Pending: {pending.get('pending', 0)}")
        print(f"死信:   {dead_count}")
        print(f"死信率: {dead_count / max(1, task_count + dead_count) * 100:.1f}%")

        await r.aclose()
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)
