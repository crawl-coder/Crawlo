#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 通用环形缓冲区 + 百分位计算工具

用于：
- downloader/p99_response_ms：AioHttpDownloader 最近 1000 条响应 RT
- pipeline/item/p99_latency_ms：Pipeline 每条 process_item 延迟
- resource/eventloop_lag_ms_*：Eventloop Lag 探针（最近 60 个 1s 采样）
- filter/duplicate_rps：最近 1min dedup duplicate 计数滑窗

简单、零依赖，不引入 numpy 等重型依赖。
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, Iterable, List, Sequence, Tuple


__all__ = [
    "RingBuffer",
    "percentile",
    "percentiles",
]


def percentile(sorted_values: Sequence[float], pct: float) -> float:
    """对已排序的序列（升序）求指定百分位值（线性插值，和 numpy.percentile 语义一致）。

    Args:
        sorted_values: 已升序排序的数值序列（允许空，返回 0.0）
        pct: 0~100 范围内的百分位（如 50 / 95 / 99）
    """
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_values[0])
    if pct <= 0:
        return float(sorted_values[0])
    if pct >= 100:
        return float(sorted_values[-1])

    # 线性插值的 rank 位置（0-based）
    k = (pct / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_values[int(k)])
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return float(d0 + d1)


def percentiles(values: Iterable[float], pcts: Sequence[float]) -> Tuple[float, ...]:
    """对任意数值序列，一次性求多个百分位（返回元组顺序与 pcts 一致）。"""
    sorted_vals: List[float] = sorted(values)
    return tuple(percentile(sorted_vals, p) for p in pcts)


class RingBuffer:
    """定长环形缓冲区：append 覆盖最旧元素，提供快速统计 & 百分位。

    线程不安全：如果需要跨任务，由调用方自行加锁（或使用单协程 owner）。

    Args:
        capacity: 容量上限（>0），超出后覆盖最旧值
    """

    __slots__ = ("_capacity", "_buf")

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("RingBuffer capacity must be positive")
        self._capacity = int(capacity)
        self._buf: Deque[float] = deque(maxlen=self._capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._buf)

    def clear(self) -> None:
        self._buf.clear()

    def append(self, value: float) -> None:
        """追加一个数值（float），容量满时自动丢弃最旧值。"""
        self._buf.append(float(value))

    def extend(self, values: Iterable[float]) -> None:
        for v in values:
            self._buf.append(float(v))

    # ---- 快速统计（O(n)，n ≤ capacity，典型 <1k）----

    def sum(self) -> float:
        return sum(self._buf)

    def mean(self) -> float:
        n = len(self._buf)
        return (sum(self._buf) / n) if n > 0 else 0.0

    def max(self) -> float:
        return max(self._buf) if self._buf else 0.0

    def min(self) -> float:
        return min(self._buf) if self._buf else 0.0

    # ---- 百分位 ----

    def percentile(self, pct: float) -> float:
        return percentile(sorted(self._buf), pct)

    def percentiles(self, pcts: Sequence[float]) -> Tuple[float, ...]:
        return percentiles(self._buf, pcts)

    # ---- 调试 ----

    def snapshot(self) -> List[float]:
        return list(self._buf)
