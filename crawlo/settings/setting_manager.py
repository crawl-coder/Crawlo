#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json
from copy import deepcopy
from importlib import import_module
from collections.abc import MutableMapping

from crawlo.settings import default_settings


class SettingManager(MutableMapping):

    def __init__(self, values=None):
        self.attributes = {}
        self.set_settings(default_settings)
        self.update_attributes(values)

    def get(self, key, default=None):
        """安全获取值，不触发递归"""
        value = self.attributes.get(key, default)
        return value if value is not None else default

    def get_int(self, key, default=0):
        return int(self.get(key, default=default))

    def get_float(self, key, default=0.0):
        return float(self.get(key, default=default))

    def get_bool(self, key, default=False):
        got = self.get(key, default=default)
        if isinstance(got, bool):
            return got
        if isinstance(got, (int, float)):
            return bool(got)
        got_lower = str(got).strip().lower()
        if got_lower in ('1', 'true'):
            return True
        if got_lower in ('0', 'false'):
            return False
        raise ValueError(
            f"Unsupported value for boolean setting: {got}. "
            "Supported values are: 0/1, True/False, '0'/'1', 'True'/'False' (case-insensitive)."
        )

    def get_list(self, key, default=None):
        values = self.get(key, default or [])
        if isinstance(values, str):
            return [v.strip() for v in values.split(',') if v.strip()]
        try:
            return list(values)
        except TypeError:
            return [values]

    def get_dict(self, key, default=None):
        value = self.get(key, default or {})
        if isinstance(value, str):
            value = json.loads(value)
        try:
            return dict(value)
        except TypeError:
            return value

    def set(self, key, value):
        self.attributes[key] = value

    def set_settings(self, module):
        if isinstance(module, str):
            module = import_module(module)
        for key in dir(module):
            if key.isupper():
                self.set(key, getattr(module, key))

    # 实现 MutableMapping 必须的方法
    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        del self.attributes[key]

    def __iter__(self):
        return iter(self.attributes)

    def __len__(self):
        return len(self.attributes)

    def __str__(self):
        return f'<Settings: {self.attributes}>'

    __repr__ = __str__

    def update_attributes(self, attributes):
        if attributes is not None:
            for key, value in attributes.items():
                self.set(key, value)

    def copy(self):
        return deepcopy(self)

    def __deepcopy__(self, memo):
        """
        自定义深度复制方法，避免复制logger等不可pickle的对象
        """
        # 创建一个新的实例
        cls = self.__class__
        new_instance = cls.__new__(cls)
        
        # 复制attributes字典，但排除不可pickle的对象
        new_attributes = {}
        for key, value in self.attributes.items():
            try:
                # 尝试深度复制值
                new_attributes[key] = deepcopy(value, memo)
            except Exception:
                # 如果复制失败，保留原始引用（对于logger等对象）
                new_attributes[key] = value
        
        # 设置新实例的attributes
        new_instance.attributes = new_attributes
        
        return new_instance