#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Item 类定义
"""
from copy import deepcopy
from pprint import pformat
from typing import Any, Iterator, Dict
from collections.abc import MutableMapping

from .base import ItemMeta
from crawlo.exceptions import ItemInitError, ItemAttributeError


class Item(MutableMapping, metaclass=ItemMeta):
    """
    数据项基类，用于定义结构化数据
    """
    FIELDS: Dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        if args:
            raise ItemInitError(f"{self.__class__.__name__} 不支持位置参数：{args}，请使用关键字参数初始化。")

        self._values: Dict[str, Any] = {}

        # 初始化字段，默认值填充
        for field_name, field_obj in self.FIELDS.items():
            if field_obj.default is not None:
                self._values[field_name] = field_obj.default

        # 覆盖默认值或设置新值
        for key, value in kwargs.items():
            self[key] = value

    def __getitem__(self, item: str) -> Any:
        return self._values[item]

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self.FIELDS:
            raise KeyError(f"{self.__class__.__name__} 不包含字段：{key}")

        field = self.FIELDS[key]
        try:
            validated_value = field.validate(value, field_name=key)
            self._values[key] = validated_value
        except Exception as e:
            error_lines = [
                "",
                "【字段校验失败】",
                f"字段名称: {key}",
                f"数据类型: {type(value)}",
                f"原始值:   {repr(value)}",
                f"是否允许空值: {field.nullable}",
                f"错误原因: {str(e)}",
                ""
            ]
            detailed_error = "\n".join(error_lines)
            raise type(e)(detailed_error) from e

    def __delitem__(self, key: str) -> None:
        del self._values[key]

    def __setattr__(self, key: str, value: Any) -> None:
        if not key.startswith("_"):
            raise AttributeError(
                f"设置字段值请使用 item[{key!r}] = {value!r}"
            )
        super().__setattr__(key, value)

    def __getattr__(self, item: str) -> Any:
        raise AttributeError(
            f"{self.__class__.__name__} 不支持字段：{item}。"
            f"请先在 `{self.__class__.__name__}` 中声明该字段，再通过 item[{item!r}] 获取。"
        )

    def __getattribute__(self, item: str) -> Any:
        try:
            field = super().__getattribute__("FIELDS")
            if isinstance(field, dict) and item in field:
                raise ItemAttributeError(
                    f"获取字段值请使用 item[{item!r}]"
                )
        except AttributeError:
            pass  # 如果 FIELDS 尚未定义，继续执行后续逻辑
        return super().__getattribute__(item)

    def __repr__(self) -> str:
        return pformat(dict(self))

    __str__ = __repr__

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return dict(self)

    def copy(self) -> "Item":
        """深拷贝当前 Item"""
        return deepcopy(self)