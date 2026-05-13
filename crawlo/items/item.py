#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Item Class Definition
"""
from copy import deepcopy
from pprint import pformat
from typing import Any, Iterator, Dict
from collections.abc import MutableMapping

from .base import ItemMeta
from .fields import Field
from crawlo.exceptions import ItemInitError, ItemAttributeError


class Item(MutableMapping, metaclass=ItemMeta):
    """
    Base data item class for defining structured data
    
    支持动态字段：未声明的字段会自动创建（allow_dynamic=True 时）
    """
    FIELDS: Dict[str, Any] = {}
    allow_dynamic: bool = True  # 是否允许动态字段

    def __init__(self, *args, **kwargs):
        if args:
            raise ItemInitError(
                f"{self.__class__.__name__} does not support positional arguments: {args}, "
                f"please use keyword arguments for initialization."
            )

        self._values: Dict[str, Any] = {}

        # Initialize fields with default values
        for field_name, field_obj in self.FIELDS.items():
            if field_obj.default is not None:
                self._values[field_name] = field_obj.default

        # Override defaults or set new values
        for key, value in kwargs.items():
            self[key] = value

    def __getitem__(self, item: str) -> Any:
        return self._values[item]

    def __setitem__(self, key: str, value: Any) -> None:
        # 支持动态字段：如果字段不存在且允许动态创建，则自动创建
        if key not in self.FIELDS:
            if getattr(self.__class__, 'allow_dynamic', True):
                # 自动创建字段定义
                self.__class__.FIELDS[key] = Field()
            else:
                raise KeyError(f"{self.__class__.__name__} does not contain field: {key}")

        field = self.FIELDS[key]
        try:
            validated_value = field.validate(value, field_name=key)
            self._values[key] = validated_value
        except (ValueError, TypeError) as e:
            error_lines = [
                "",
                "[Field Validation Failed]",
                f"Field Name: {key}",
                f"Data Type: {type(value)}",
                f"Original Value:   {repr(value)}",
                f"Nullable: {field.nullable}",
                f"Error Reason: {str(e)}",
                ""
            ]
            detailed_error = "\n".join(error_lines)
            raise type(e)(detailed_error) from e

    def __delitem__(self, key: str) -> None:
        del self._values[key]

    def __setattr__(self, key: str, value: Any) -> None:
        if not key.startswith("_"):
            raise AttributeError(
                f"Use item[{key!r}] = {value!r} to set field values"
            )
        super().__setattr__(key, value)

    def __getattr__(self, item: str) -> Any:
        raise AttributeError(
            f"{self.__class__.__name__} does not support field: {item}. "
            f"Please declare the field in `{self.__class__.__name__}` first, "
            f"then use item[{item!r}] to access it."
        )

    def __getattribute__(self, item: str) -> Any:
        try:
            field = super().__getattribute__("FIELDS")
            if isinstance(field, dict) and item in field:
                raise ItemAttributeError(
                    f"Use item[{item!r}] to access field values"
                )
        except AttributeError:
            pass  # If FIELDS is not yet defined, continue with normal logic
        return super().__getattribute__(item)

    def __repr__(self) -> str:
        return pformat(dict(self))

    __str__ = __repr__

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return dict(self)

    def copy(self) -> "Item":
        """Deep copy the current Item"""
        return deepcopy(self)
