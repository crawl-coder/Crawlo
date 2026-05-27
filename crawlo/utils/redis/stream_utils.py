#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis Streams 工具函数

提供版本检测、Consumer Group 管理、单 Stream 读取等辅助功能。
"""
from typing import Optional, Tuple, List, Dict, Any


async def detect_redis_version(redis_client) -> Tuple[int, int, int]:
    """
    检测 Redis 服务器版本。

    Returns:
        (major, minor, patch) 版本元组
    """
    info = await redis_client.info("server")
    version_str = info.get("redis_version", "0.0.0")
    parts = version_str.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


async def supports_xautoclaim(redis_client) -> bool:
    """检查 Redis 是否支持 XAUTOCLAIM（需要 6.2+）"""
    major, minor, _ = await detect_redis_version(redis_client)
    return major > 6 or (major == 6 and minor >= 2)


async def supports_xstream(redis_client) -> bool:
    """检查 Redis 是否支持 Stream 基本功能（需要 5.0+）"""
    major, _, _ = await detect_redis_version(redis_client)
    return major >= 5


async def get_version_str(redis_client) -> str:
    """获取可读的 Redis 版本字符串"""
    major, minor, patch = await detect_redis_version(redis_client)
    return f"{major}.{minor}.{patch}"


async def create_consumer_group_safe(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    mkstream: bool = True
) -> bool:
    """
    安全地创建 Consumer Group（处理 BUSYGROUP 竞态）。

    Returns:
        True: 组已创建或已存在
        False: 创建失败（非 BUSYGROUP 错误）
    """
    try:
        await redis_client.xgroup_create(
            stream, group, id="0", mkstream=mkstream
        )
        return True
    except Exception as e:
        if "BUSYGROUP" in str(e):
            # 组已被其他 Worker 创建，属于正常并发场景
            return True
        return False


async def get_pending_count(redis_client, stream: str, group: str) -> int:
    """
    获取 Pending 消息总数。

    使用 XPENDING 的简化形式（无参数），返回摘要信息。
    """
    try:
        result = await redis_client.xpending(stream, group)
        if result and isinstance(result, dict):
            return result.get("pending", 0)
    except Exception:
        pass
    return 0


async def get_stream_info(redis_client, stream: str) -> Optional[Dict[str, Any]]:
    """获取 Stream 基本信息"""
    try:
        info = await redis_client.xinfo_stream(stream)
        return {
            "length": info.get("length", 0),
            "first_entry": info.get("first-entry"),
            "last_entry": info.get("last-entry"),
            "groups": info.get("groups", 0),
        }
    except Exception:
        return None


async def get_consumer_group_info(
    redis_client, stream: str, group: str
) -> Optional[List[Dict[str, Any]]]:
    """获取 Consumer Group 中的 Consumer 信息"""
    try:
        consumers = await redis_client.xinfo_consumers(stream, group)
        return [
            {
                "name": c.get("name"),
                "pending": c.get("pending", 0),
                "idle": c.get("idle", 0),
            }
            for c in consumers
        ]
    except Exception:
        return None


async def stream_read(
    redis_client,
    group: str,
    consumer: str,
    stream: str,
    count: int = 1,
    block: Optional[int] = None,
) -> Optional[List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]]:
    """
    单 Stream 读取。

    Args:
        redis_client: Redis 客户端
        group: Consumer Group 名称
        consumer: Consumer 名称
        stream: Stream key
        count: 每次读取消息数量
        block: 阻塞超时（ms），None 或 0 表示非阻塞

    Returns:
        读取到的消息列表，None 表示无消息

    Note:
        Redis 的 BLOCK 0 表示"无限等待"而非"不等待"，
        因此非阻塞读取时不能传 block=0，应省略 block 参数。
    """
    try:
        if block and block > 0:
            msgs = await redis_client.xreadgroup(
                group, consumer,
                {stream: ">"}, count=count, block=block
            )
        else:
            msgs = await redis_client.xreadgroup(
                group, consumer,
                {stream: ">"}, count=count
            )
        if msgs:
            return msgs
    except Exception:
        pass

    return None


# 兼容旧代码的别名
async def dual_stream_read(
    redis_client,
    group: str,
    consumer: str,
    high_stream: str,
    low_stream: str,
    count: int = 1,
    block: int = 5000,
) -> Optional[List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]]:
    """
    [已废弃] 双 Stream 读取，保留仅为兼容。

    新代码应使用 stream_read()。
    当 high_stream == low_stream 时，等同于单 Stream 读取。
    """
    import warnings
    warnings.warn(
        "dual_stream_read is deprecated, use stream_read instead",
        DeprecationWarning,
        stacklevel=2,
    )
    # 如果 high == low，直接单 stream 读取
    if high_stream == low_stream:
        return await stream_read(redis_client, group, consumer, high_stream, count=count, block=block)

    # 兼容旧逻辑：先非阻塞读 high，再读 low
    try:
        msgs = await redis_client.xreadgroup(
            group, consumer,
            {high_stream: ">"}, count=count
        )
        if msgs:
            return msgs
    except Exception:
        pass

    try:
        if block and block > 0:
            msgs = await redis_client.xreadgroup(
                group, consumer,
                {low_stream: ">"}, count=count, block=block
            )
        else:
            msgs = await redis_client.xreadgroup(
                group, consumer,
                {low_stream: ">"}, count=count
            )
        if msgs:
            return msgs
    except Exception:
        pass

    return None


async def claim_pending_manual(
    redis_client,
    stream: str,
    group: str,
    consumer: str,
    min_idle_ms: int = 60000,
    batch_size: int = 10,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    手动回收超时 Pending 消息（兼容 Redis 5.0-6.1，无 XAUTOCLAIM 时使用）。

    步骤：
    1. XPENDING 查询超时消息
    2. XCLAIM 转移所有权

    Returns:
        被回收的消息列表 [(message_id, data), ...]
    """
    claimed = []

    try:
        # 获取 pending 消息列表
        pending_result = await redis_client.xpending_range(
            stream, group, min="-", max="+", count=batch_size
        )

        if not pending_result:
            return claimed

        # 筛选超时消息
        timed_out_ids = [
            entry["message_id"]
            for entry in pending_result
            if entry.get("idle", 0) >= min_idle_ms
        ]

        if not timed_out_ids:
            return claimed

        # XCLAIM 转移所有权
        claimed_msgs = await redis_client.xclaim(
            stream, group, consumer,
            min_idle_time=min_idle_ms,
            message_ids=timed_out_ids,
        )

        for msg in claimed_msgs:
            if msg:
                msg_id = msg[0] if isinstance(msg, tuple) else msg
                msg_data = msg[1] if isinstance(msg, tuple) and len(msg) > 1 else {}
                claimed.append((msg_id, msg_data))

    except Exception:
        pass

    return claimed


__all__ = [
    "detect_redis_version",
    "supports_xautoclaim",
    "supports_xstream",
    "get_version_str",
    "create_consumer_group_safe",
    "get_pending_count",
    "get_stream_info",
    "get_consumer_group_info",
    "stream_read",
    "dual_stream_read",
    "claim_pending_manual",
]
