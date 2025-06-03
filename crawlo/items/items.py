#!/usr/bin/python
# -*- coding: UTF-8 -*-
from copy import deepcopy
from pprint import pformat
from typing import Any, Iterator, Dict
from collections.abc import MutableMapping

from crawlo.items import ItemMeta, Field
from crawlo.exceptions import ItemInitError, ItemAttributeError


class Item(MutableMapping, metaclass=ItemMeta):
    FIELDS: Dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        if args:
            raise ItemInitError(f"{self.__class__.__name__} 不支持位置参数：{args}，请使用关键字参数初始化。")
        if kwargs:
            for key, value in kwargs.items():
                self[key] = value

        self._values: Dict[str, Any] = {}

    def __getitem__(self, item: str) -> Any:
        return self._values[item]

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self.FIELDS:
            raise KeyError(f"{self.__class__.__name__} 不包含字段：{key}")
        self._values[key] = value

    def __delitem__(self, key: str) -> None:
        del self._values[key]

    def __setattr__(self, key: str, value: Any) -> None:
        if not key.startswith("_"):
            raise AttributeError(
                f"设置字段值请使用 item[{key!r}] = {value!r}"
            )
        super().__setattr__(key, value)

    def __getattr__(self, item: str) -> Any:
        # 当获取不到属性时触发
        raise AttributeError(
            f"{self.__class__.__name__} 不支持字段：{item}。"
            f"请先在 `{self.__class__.__name__}` 中声明该字段，再通过 item[{item!r}] 获取。"
        )

    def __getattribute__(self, item: str) -> Any:
        # 属性拦截器，只要访问属性就会进入该方法
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
        return dict(self)

    def copy(self) -> "Item":
        return deepcopy(self)


if __name__ == '__main__':
    class TestItem(Item):
        url = Field()
        title = Field()

    test_item = TestItem()
    test_item['title'] = '百度首页'
    test_item['url'] = 'http://example.com'
    # test_item.title = 'fffff'
    print(test_item.title)