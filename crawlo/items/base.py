#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
基础元类定义
"""
from abc import ABCMeta

from crawlo.items import Field


class ItemMeta(ABCMeta):
    """
    元类，用于自动收集 Item 类中的 Field 定义
    """

    def __new__(mcs, name, bases, attrs):
        fields = {}
        cls_attrs = {}

        # 收集所有 Field 实例
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            else:
                cls_attrs[attr_name] = attr_value

        # 创建类实例
        cls_instance = super().__new__(mcs, name, bases, cls_attrs)
        cls_instance.FIELDS = fields

        return cls_instance