#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
命令行入口：crawlo dead-letter，死信队列管理

用法：
    crawlo dead-letter list <project> <spider>      查看死信 (--limit N)
    crawlo dead-letter retry <project> <spider>     单轮重新入队 (--count N)
    crawlo dead-letter replay <project> <spider>    定时重放：
                                                    [--max-per-round N] 每轮上限（默认 100）
                                                    [--interval S]      轮间隔秒（默认 0=单轮）
                                                    [--rounds N]        轮数上限（默认无限，
                                                                        需配合 --interval；
                                                                        后台自动化建议用户 cron）
    crawlo dead-letter stats <project> <spider>     查看统计

重放语义：把死信 XADD 回主 Stream（retry_count 归零、剥离死信元数据字段）、
再从死信 Stream 移除——与 Worker 端死信升级互为逆操作，不重复入队。
"""
import asyncio
import sys

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
    elif action == "retry":
        asyncio.run(_retry_dead_letters(project, spider, _arg_int(args, "--count", 100)))
    elif action == "replay":
        asyncio.run(_replay_dead_letters(
            project,
            spider,
            max_per_round=_arg_int(args, "--max-per-round", 100),
            interval=_arg_float(args, "--interval", 0),
            rounds=_arg_int(args, "--rounds", 0),
        ))
    elif action == "stats":
        asyncio.run(_show_stats(project, spider))
    else:
        _print_usage()


def _arg_int(args, flag, default):
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                print(f"无效的 {flag} 值: {args[i + 1]!r}")
                sys.exit(1)
    return default


def _arg_float(args, flag, default):
    for i, arg in enumerate(args):
        if arg == flag and i + 1 < len(args):
            try:
                return float(args[i + 1])
            except ValueError:
                print(f"无效的 {flag} 值: {args[i + 1]!r}")
                sys.exit(1)
    return default


def _print_usage():
    print("crawlo dead-letter — 死信队列管理")
    print()
    print("用法:")
    print("  crawlo dead-letter list <project> <spider>    查看死信 (--limit N)")
    print("  crawlo dead-letter retry <project> <spider>   单轮重新入队 (--count N)")
    print("  crawlo dead-letter replay <project> <spider>")
    print("      [--max-per-round N] [--interval S] [--rounds N]")
    print("                                                定时重放（默认单轮）")
    print("  crawlo dead-letter stats <project> <spider>   查看统计")


def _dead_keys(project, spider):
    return (
        f"crawlo:{project}:{spider}:stream:failed",
        f"crawlo:{project}:{spider}:stream:tasks",
    )


async def _replay_round(r, project, spider, limit):
    """执行一轮重放：XADD 回主 Stream + XDEL 死信。返回本轮移动条数。"""
    dead_key, stream_key = _dead_keys(project, spider)
    msgs = await r.xrevrange(dead_key, count=limit)
    moved = 0
    for msg_id, fields in msgs:
        new_fields = {
            k: v for k, v in fields.items()
            if k not in (b"retry_count", b"dead_at", b"dead_reason",
                         b"original_message_id")
        }
        new_fields[b"retry_count"] = b"0"
        await r.xadd(stream_key, new_fields, maxlen=100000, approximate=True)
        await r.xdel(dead_key, msg_id)
        moved += 1
    return moved


async def _replay_dead_letters(project, spider, max_per_round=100, interval=0, rounds=0):
    """定时重放死信。

    - interval<=0：单轮模式（等价旧 retry 行为，参数名更直观）；
    - interval>0 ：循环重放直到死信清空 / 达到 --rounds 上限 / 用户中断。
      后台自动化建议由用户以 cron 调用单轮命令实现，框架不做常驻任务。
    """
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://127.0.0.1:6379/0")

        total = 0
        round_no = 0
        try:
            while True:
                moved = await _replay_round(r, project, spider, max_per_round)
                round_no += 1
                total += moved
                dead_key, _ = _dead_keys(project, spider)
                remaining = await r.xlen(dead_key)
                print(f"[第 {round_no} 轮] 重放 {moved} 条，剩余死信 {remaining}")

                if remaining == 0:
                    print(f"完成：死信已清空，累计重放 {total} 条")
                    return
                if interval <= 0:
                    print(f"单轮模式结束：剩余 {remaining} 条"
                          f"（使用 --interval <秒> 开启循环重放）")
                    return
                if rounds and round_no >= rounds:
                    print(f"达到 --rounds {rounds} 轮上限：累计重放 {total} 条，"
                          f"剩余 {remaining} 条")
                    return
                await asyncio.sleep(interval)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print(f"\n已中断：累计重放 {total} 条")
        finally:
            await r.aclose()
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)


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
