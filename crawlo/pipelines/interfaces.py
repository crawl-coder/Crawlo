#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
管道层接口定义
==============
IPipeline（数据管道接口）。
"""
from abc import abstractmethod
from typing import (
    Protocol, runtime_checkable, TYPE_CHECKING
)

if TYPE_CHECKING:
    from crawlo.items import Item


# ==================== 管道接口 ====================

@runtime_checkable
class IPipeline(Protocol):
    """
    数据管道接口

    负责 Item 的处理、清洗、存储等操作。

    实现示例：
        class MySQLPipeline(IPipeline):
            async def process_item(self, item: Item) -> Item:
                await self.db.insert(item.to_dict())
                return item

            async def close(self) -> None:
                await self.db.close()
    """

    @abstractmethod
    async def process_item(self, item: 'Item') -> 'Item':
        """
        处理 Item

        Args:
            item: 待处理的 Item

        Returns:
            Item: 处理后的 Item（传递给下一个管道）

        Raises:
            ItemDiscard: 丢弃 Item，不传递给后续管道
            DropItem: 同 ItemDiscard（别名）
        """
        ...

    async def open(self) -> None:
        """
        打开管道（可选实现）

        用于初始化资源，如数据库连接。
        """
        ...

    async def close(self) -> None:
        """
        关闭管道（可选实现）

        用于清理资源，如关闭数据库连接。
        """
        ...


__all__ = [
    'IPipeline',
]
