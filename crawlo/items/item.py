#!/usr/bin/python
# -*- coding:UTF-8 -*-
from copy import deepcopy
from pprint import pformat
from collections.abc import MutableMapping

from crawlo.exceptions import ItemInitError, ItemAttributeError
from crawlo.items import ItemMeta


class Item(MutableMapping, metaclass=ItemMeta):
    FIELDS: dict

    def __init__(self, *args, **kwargs):
        self._values = {}
        if args:
            raise ItemInitError(f'{self.__class__.__name__}: position {args} is not supported. use keyword args.')
        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getitem__(self, item):
        return self._values[item]

    def __setitem__(self, key, value):
        if key in self.FIELDS:
            self._values[key] = value
        else:
            raise KeyError(f'{self.__class__.__name__} does not support field: {key}')

    def __delitem__(self, key):
        del self._values[key]

    def __setattr__(self, key, value):
        if not key.startswith('_'):
            raise AttributeError(f'please use item[{key!r}] = {value!r} to set field value.')
        super().__setattr__(key, value)

    def __getattr__(self, item):
        # 当获取不到属性时触发
        raise AttributeError(
            f'{self.__class__.__name__} does not support field：{item}. Please add the `{item}` field to the {self.__class__.__name__}, and use the `item[{item!r}]` to get field value.'
        )

    def __getattribute__(self, item):
        # 属性拦截器，只要访问属性就会进入该方法
        field = super().__getattribute__('FIELDS')
        if item in field:
            raise ItemAttributeError(f'please use item[{item!r} to get field value.')
        else:
            return super().__getattribute__(item)

    def __repr__(self):
        return pformat(dict(self))

    __str__ = __repr__

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def to_dict(self):
        return dict(self)

    def copy(self):
        return deepcopy(self)
