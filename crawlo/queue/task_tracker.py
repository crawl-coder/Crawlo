#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
任务生命周期追踪

管理分布式任务的状态流转：分配 → 处理中 → 完成/重试/死信。
提供错误分类逻辑，区分可恢复错误与终态错误。
"""
from enum import Enum
from typing import Optional, Dict, Any


class TaskResult(Enum):
    """任务处理结果分类"""
    ACK = "ack"            # 彻底完成（包括 HTTP 4xx/5xx 等终态错误）
    RETRY = "retry"        # 可重试（网络超时、连接拒绝等瞬态错误）
    DEAD_LETTER = "dead"   # 超过重试次数，转入死信


class TaskTracker:
    """
    任务生命周期追踪

    在每个 Worker 中追踪其当前处理的任务状态。
    分布式状态下，任务所有权由 Redis Stream Consumer Group 管理，
    TaskTracker 只负责本 Worker 内的状态记录和错误分类。

    使用示例：
        tracker = TaskTracker(consumer_name="worker-abc123")
        task_id = await tracker.on_dispatched(request)
        try:
            await process(request)
            await tracker.on_completed(task_id)
        except Exception as e:
            result = tracker.classify_error(e)
            await tracker.on_failed(task_id, e, result)
    """

    def __init__(self, consumer_name: str = "default"):
        self.consumer_name = consumer_name
        self._processing: Dict[str, Dict[str, Any]] = {}  # message_id -> task info
        self._stats = {
            "completed": 0,
            "retried": 0,
            "dead_letter": 0,
            "total": 0,
        }

    # ---- 生命周期方法 ----

    async def on_dispatched(self, request, message_id: str) -> str:
        """
        任务已分配给本 Consumer（XREADGROUP 返回后调用）。

        Args:
            request: Request 对象
            message_id: Stream 消息 ID

        Returns:
            message_id（供后续 ACK/NACK 使用）
        """
        self._processing[message_id] = {
            "request": request,
            "dispatched_at": __import__("time").time(),
            "retry_count": getattr(request, "meta", {}).get("__stream_retry_count", 0) if hasattr(request, "meta") else 0,
        }
        self._stats["total"] += 1
        return message_id

    async def on_completed(self, message_id: str):
        """任务处理完成（预期调用 XACK）"""
        self._processing.pop(message_id, None)
        self._stats["completed"] += 1

    async def on_failed(self, message_id: str, error: Exception, result: TaskResult = TaskResult.RETRY):
        """
        任务处理失败。

        Args:
            message_id: Stream 消息 ID
            error: 异常信息
            result: 处理结果分类
        """
        task_info = self._processing.pop(message_id, {"request": None})
        request = task_info.get("request")

        if result == TaskResult.RETRY:
            self._stats["retried"] += 1
        elif result == TaskResult.DEAD_LETTER:
            self._stats["dead_letter"] += 1
        else:
            # ACK for failed tasks (终态错误)
            self._stats["completed"] += 1

    async def on_timeout(self, message_id: str):
        """任务超时被其他 Consumer XCLAIM 回收（本 Worker 视角）"""
        self._processing.pop(message_id, None)

    # ---- 错误分类 ----

    def classify_error(self, error: Exception) -> TaskResult:
        """
        根据异常类型决定任务处理策略。

        规则：
        - 网络超时/连接错误 → RETRY（可重试）
        - HTTP 429（限流） → RETRY（等待后重试）
        - HTTP 403 → 视情况（反爬拦截可能需要 RETRY）
        - HTTP 500 → ACK（服务端终态错误，重试无意义）
        - 解析错误 → ACK（非可恢复）
        - 未知错误 → RETRY（保守策略）
        """
        error_type = type(error).__name__
        error_str = str(error).lower()

        # 网络层错误 → 可重试
        network_errors = (
            "TimeoutError", "ConnectionError", "ConnectionRefusedError",
            "ConnectionResetError", "OSError", "Timeout",
            "asyncio.TimeoutError",
        )
        if error_type in network_errors:
            return TaskResult.RETRY

        # 按错误消息判断
        retry_keywords = ("timeout", "connection", "reset", "refused", "timed out")
        dead_keywords = ("not found", "404", "500", "internal server")

        if any(kw in error_str for kw in retry_keywords):
            return TaskResult.RETRY
        if any(kw in error_str for kw in dead_keywords):
            return TaskResult.ACK

        return TaskResult.RETRY  # 默认可重试

    # ---- 查询方法 ----

    @property
    def processing_count(self) -> int:
        """当前处理中的任务数"""
        return len(self._processing)

    @property
    def stats(self) -> Dict[str, int]:
        """统计信息"""
        return dict(self._stats)

    def get_processing_tasks(self) -> Dict[str, Any]:
        """获取当前处理中的任务列表（用于优雅关闭时的排查）"""
        return {
            msg_id: {
                "url": info.get("request").url if info.get("request") else "unknown",
                "dispatched_at": info.get("dispatched_at"),
            }
            for msg_id, info in self._processing.items()
        }


__all__ = [
    "TaskResult",
    "TaskTracker",
]
