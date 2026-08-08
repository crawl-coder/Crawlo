#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
数据层异常定义
=============
Item 数据处理、验证、丢弃相关异常。
"""
from typing import Optional, Any

from crawlo.core.errors import CrawloException


# ============= 数据处理异常 =============
class DataException(CrawloException):
    """数据处理异常基类"""
    pass


class ItemInitError(DataException):
    """Item初始化错误。当Item实例创建失败时抛出"""
    pass


class ItemAttributeError(DataException, AttributeError):
    """Item属性错误。当访问不存在的Item属性时抛出"""
    pass


class ItemValidationError(DataException):
    """Item字段验证错误。当Item字段值不符合验证规则时抛出"""

    def __init__(
        self,
        message: str = "",
        field_name: Optional[str] = None,
        value: Any = None
    ) -> None:
        super().__init__(message)
        self.field_name = field_name
        self.value = value


class ItemDiscard(DataException):
    """
    Item被丢弃异常

    注意：这不是一个真正的错误，而是用于流程控制，
    表示Item应该被管道丢弃（例如重复数据）。

    Attributes:
        msg: 丢弃原因
    """

    def __init__(self, msg: str = "") -> None:
        self.msg = msg
        super().__init__(msg)

    def __str__(self) -> str:
        return f"ItemDiscard: {self.msg}"


# 别名
DropItem = ItemDiscard


# ============= 导出 =============
__all__ = [
    'DataException',
    'ItemInitError',
    'ItemAttributeError',
    'ItemValidationError',
    'ItemDiscard',
    'DropItem',
]
