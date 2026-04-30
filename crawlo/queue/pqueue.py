# -*- coding:UTF-8 -*-
import asyncio
from asyncio import PriorityQueue
from typing import Optional, Any


class SpiderPriorityQueue(PriorityQueue):
    """带超时功能的异步优先级队列"""

    def __init__(self, maxsize: int = 0) -> None:
        """初始化队列，maxsize为0表示无大小限制"""
        super().__init__(maxsize)

    async def get(self, timeout: float = 0.01) -> Optional[Any]:
        """
        异步获取队列元素，带超时功能

        Args:
            timeout: 超时时间（秒），默认0.01秒

        Returns:
            队列元素(优先级, 值)或None(超时)
        """
        try:
            async with asyncio.timeout(timeout):
                item = await super().get()
                return item
        except asyncio.TimeoutError:
            return None

    def qsize(self) -> int:
        """获取队列大小"""
        return super().qsize()

    async def close(self) -> None:
        """关闭队列（空实现，用于与Redis队列接口保持一致）"""
        pass
