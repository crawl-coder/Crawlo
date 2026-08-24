#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
DLQ 定时重放集成测试（v1.7.5 A2：crawlo dead-letter replay）

使用真实 Redis（与既有分布式测试同约定）。验证：
1. 单轮重放：死信 XADD 回主 Stream、从 DLQ 移除、retry_count 归零、
   死信元数据字段被剥离；
2. --max-per-round 生效：单轮只移动 N 条，剩余留在 DLQ；
3. 循环模式（--interval + --rounds）：多轮直到清空或达轮数上限；
4. 不重复入队：重放后主 Stream 条数精确等于移动条数。
"""
import time
import uuid

import pytest
import redis.asyncio as aioredis

from crawlo.commands import dead_letter

pytestmark = pytest.mark.redis


@pytest.fixture
def ns():
    """独立命名空间 + 连接，测试后清理"""
    project = "dlqtest"
    spider = f"s{uuid.uuid4().hex[:8]}"
    r = aioredis.from_url("redis://127.0.0.1:6379/0")
    yield project, spider, r
    # 清理本测试产生的所有 key
    dead_key, stream_key = dead_letter._dead_keys(project, spider)
    group_key = f"crawlo:{project}:{spider}:group:workers"
    for key in (dead_key, stream_key, group_key):
        try:
            r.delete(key)
        except Exception:
            pass


def _seed_dead(r, project: str, spider: str, n: int):
    """向 DLQ 注入 n 条带完整元数据的假死信"""
    dead_key, _ = dead_letter._dead_keys(project, spider)
    pipe = r.pipeline()
    for i in range(n):
        pipe.xadd(dead_key, {
            b"data": f'{{"url":"http://t/{i}"}}'.encode(),
            b"dead_reason": b"max_retry_exceeded",
            b"retry_count": b"3",
            b"dead_at": str(time.time()).encode(),
            b"original_message_id": b"1700000000000-0",
        })
    return pipe.execute()


class TestReplay:

    @pytest.mark.asyncio
    async def test_single_round_moves_and_cleans(self, ns):
        project, spider, r = ns
        ids = await _seed_dead(r, project, spider, 3)

        moved = await dead_letter._replay_round(r, project, spider, limit=100)
        assert moved == 3

        dead_key, stream_key = dead_letter._dead_keys(project, spider)
        assert await r.xlen(dead_key) == 0
        entries = await r.xrange(stream_key)
        assert len(entries) == 3

        fields = dict(entries[0][1])
        assert fields[b"retry_count"] == b"0"                      # 计数归零
        assert b"dead_reason" not in fields                        # 元数据剥离
        assert b"dead_at" not in fields
        assert b"original_message_id" not in fields
        # 业务负载保留（XREVRANGE 消费 → 主流顺序为 t/2,t/1,t/0，用集合断言）
        payloads = {dict(e[1])[b"data"] for e in entries}
        assert payloads == {b'{"url":"http://t/0"}',
                            b'{"url":"http://t/1"}',
                            b'{"url":"http://t/2"}'}
        assert len(ids) == 3                                       # 源消息 id 已失效

    @pytest.mark.asyncio
    async def test_max_per_round_bounds_movement(self, ns):
        project, spider, r = ns
        await _seed_dead(r, project, spider, 5)

        moved = await dead_letter._replay_round(r, project, spider, limit=2)
        assert moved == 2

        dead_key, stream_key = dead_letter._dead_keys(project, spider)
        assert await r.xlen(dead_key) == 3
        assert await r.xlen(stream_key) == 2

    @pytest.mark.asyncio
    async def test_loop_until_empty(self, ns):
        """循环模式：多轮直到清空（rounds 上限不触发）"""
        project, spider, r = ns
        await _seed_dead(r, project, spider, 5)

        await dead_letter._replay_dead_letters(
            project, spider, max_per_round=2, interval=0.02, rounds=0,
        )

        dead_key, stream_key = dead_letter._dead_keys(project, spider)
        assert await r.xlen(dead_key) == 0
        assert await r.xlen(stream_key) == 5                       # 不重复入队

    @pytest.mark.asyncio
    async def test_loop_respects_rounds_cap(self, ns):
        """--rounds 上限：达到后停止并保留剩余死信"""
        project, spider, r = ns
        await _seed_dead(r, project, spider, 5)

        await dead_letter._replay_dead_letters(
            project, spider, max_per_round=2, interval=0.02, rounds=1,
        )

        dead_key, stream_key = dead_letter._dead_keys(project, spider)
        assert await r.xlen(dead_key) == 3
        assert await r.xlen(stream_key) == 2

    @pytest.mark.asyncio
    async def test_replay_empty_dlq_is_noop(self, ns):
        project, spider, r = ns
        moved = await dead_letter._replay_round(r, project, spider, limit=10)
        assert moved == 0

    @pytest.mark.asyncio
    async def test_arg_parsing(self):
        args = ["dead-letter", "replay", "p", "s",
                "--max-per-round", "7", "--interval", "1.5", "--rounds", "3"]
        assert dead_letter._arg_int(args, "--max-per-round", 100) == 7
        assert dead_letter._arg_float(args, "--interval", 0) == 1.5
        assert dead_letter._arg_int(args, "--rounds", 0) == 3
        assert dead_letter._arg_int(args, "--missing", 42) == 42

    @pytest.mark.asyncio
    async def test_legacy_retry_alias_removed_from_replay_path(self):
        """replay 与 retry 分离后，旧别名不再走 retry 的 --count 参数路径"""
        # retry 只认 --count；replay 只认 --max-per-round
        args = ["dead-letter", "retry", "p", "s", "--count", "9"]
        assert dead_letter._arg_int(args, "--count", 100) == 9
        assert dead_letter._arg_int(args, "--max-per-round", 100) == 100
