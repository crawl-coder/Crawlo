# -*- coding:UTF-8 -*-
import sys
import asyncio
import warnings
from urllib.parse import urlparse
from asyncio import PriorityQueue
from redis.asyncio import from_url
from typing import Any, Optional, Dict, Annotated
from pydantic import (
    BaseModel,
    Field,
    model_validator
)

from crawlo import Request
from crawlo.settings.default_settings import REDIS_URL


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


class TaskModel(BaseModel):
    """爬虫任务数据模型 (完全兼容Pydantic V2)"""
    url: Annotated[str, Field(min_length=1, max_length=2000, examples=["https://example.com"])]
    meta: Dict[str, Any] = Field(default_factory=dict)
    priority: Annotated[int, Field(default=0, ge=0, le=10, description="0=最高优先级")]

    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证URL格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL必须以 http:// 或 https:// 开头')

        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError('URL缺少有效域名')

        return v.strip()

    @model_validator(mode='after')
    def validate_priority_logic(self) -> 'TaskModel':
        """跨字段验证示例"""
        if 'admin' in self.url and self.priority > 5:
            self.priority = 5  # 自动调整管理页面的优先级
        return self


class DistributedPriorityQueue:
    def __init__(
            self,
            redis_url: str,
            queue_name: str = "spider_queue",
            max_connections: int = 10,
            health_check_interval: int = 30
    ):
        """
        Args:
            redis_url: redis://[:password]@host:port[/db]
            queue_name: Redis有序集合键名
            max_connections: 连接池大小
            health_check_interval: 连接健康检查间隔(秒)
        """
        self.redis = from_url(
            redis_url,
            max_connections=max_connections,
            health_check_interval=health_check_interval,
            socket_keepalive=True,
            decode_responses=True
        )
        self.queue_name = queue_name

    async def put(self, task: TaskModel) -> bool:
        """
        添加任务到队列（使用Pydantic V2的model_dump_json）

        Args:
            task: 已验证的TaskModel实例

        Returns:
            bool: 是否成功添加 (Redis的ZADD返回添加数量)
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            task_str = task.model_dump_json()  # 正确使用V2的序列化方法
        return await self.redis.zadd(
            self.queue_name,
            {task_str: task.priority}
        ) > 0

    async def get(self, timeout: float = 1.0) -> Optional[TaskModel]:
        """
        获取优先级最高的任务（自动验证）

        Args:
            timeout: 阻塞超时时间(秒)

        Returns:
            TaskModel实例或None(超时/队列空)
        """
        try:
            result = await self.redis.bzpopmax(
                self.queue_name,
                timeout=timeout
            )
            if result:
                _, task_str, _ = result
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=DeprecationWarning)
                    return TaskModel.model_validate_json(task_str)  # 正确使用V2的反序列化方法
        except Exception as e:
            print(f"任务获取失败: {type(e).__name__}: {e}")
        return None

    async def aclose(self):
        """安全关闭连接"""
        await self.redis.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()


# 使用示例
async def demo():
    async with DistributedPriorityQueue(
            REDIS_URL,
            max_connections=20,
            health_check_interval=10
    ) as queue:
        # 添加任务（自动触发验证）
        task = TaskModel(
            url="https://example.com/1",
            priority=1,
            meta={"depth": 2}
        )

        if await queue.put(task):
            print(f"任务添加成功: {task.url}")

        # 获取任务
        if result := await queue.get(timeout=2.0):
            print(f"获取任务: {result.url} (优先级={result.priority})")
            print(f"元数据: {result.meta}")


if __name__ == "__main__":
    asyncio.run(demo())