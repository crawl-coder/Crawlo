#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
基础元类定义
"""
from abc import ABCMeta
from .fields import Field

class ItemMeta(ABCMeta):
    def __new__(mcs, name, bases, attrs):
        fields = {}
        cls_attrs = {}

        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            else:
                cls_attrs[attr_name] = attr_value

        cls_instance = super().__new__(mcs, name, bases, cls_attrs)
        cls_instance.FIELDS = fields
        return cls_instance