#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
共享 Mock Item 类
提供跨测试文件统一使用的模拟数据项，避免重复定义。
"""

from crawlo import Item
from crawlo.items.fields import Field


class MockItem:
    """通用模拟数据项（独立实现，适用于指纹生成等无框架依赖的测试）"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        """转换为字典（排除私有属性）"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


class MockDataItem(Item):
    """框架风格模拟数据项（继承自 crawlo.Item，适用于管道/集成测试）"""
    title = Field(default='')
    url = Field(default='')
