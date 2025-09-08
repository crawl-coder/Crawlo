# -*- coding:UTF-8 -*-
import json
import sys
import asyncio
from asyncio import PriorityQueue
from typing import Optional


from crawlo import Request


class SpiderPriorityQueue(PriorityQueue):
    """带超时功能的异步优先级队列"""

    def __init__(self, maxsize: int = 0) -> None:
        """初始化队列，maxsize为0表示无大小限制"""
        super().__init__(maxsize)

    async def get(self, timeout: float = 0.1) -> Optional[Request]:
        """
        异步获取队列元素，带超时功能

        Args:
            timeout: 超时时间（秒），默认0.1秒

        Returns:
            队列元素(优先级, 值)或None(超时)
        """
        try:
            # 根据Python版本选择超时实现方式
            if sys.version_info >= (3, 11):
                async with asyncio.timeout(timeout):
                    return await super().get()
            else:
                return await asyncio.wait_for(super().get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
