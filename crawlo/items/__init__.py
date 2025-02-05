#!/usr/bin/python
# -*- coding:UTF-8 -*-
from abc import ABCMeta


class Field(dict):
    pass


class ItemMeta(ABCMeta):
    """
    元类
    """
    def __new__(mcs, name, bases, attrs):
        field = {}
        for k, v in attrs.items():
            if isinstance(v, Field):
                field[k] = v
        cls_instance = super().__new__(mcs, name, bases, attrs)
        cls_instance.FIELDS = field
        return cls_instance
