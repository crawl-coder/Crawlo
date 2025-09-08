#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Field 类定义
"""

from typing import Any, Optional, Type


class Field:
    """
    字段定义类，用于定义 Item 的字段属性和验证规则
    """
    def __init__(
        self,
        nullable: bool = True,
        *,
        default: Any = None,
        field_type: Optional[Type] = None,
        max_length: Optional[int] = None,
        description: str = ""
    ):
        self.nullable = nullable
        self.default = default
        self.field_type = field_type
        self.max_length = max_length
        self.description = description

    def validate(self, value: Any, field_name: str = "") -> Any:
        """
        验证字段值是否符合规则
        """
        if value is None or (isinstance(value, str) and value.strip() == ""):
            if self.default is not None:
                return self.default
            elif not self.nullable:
                raise ValueError(
                    f"字段 '{field_name}' 不允许为空。"
                )

        if value is not None and not (isinstance(value, str) and value.strip() == ""):
            if self.field_type and not isinstance(value, self.field_type):
                raise TypeError(
                    f"字段 '{field_name}' 类型错误：期望类型 {self.field_type}, 得到 {type(value)}，值：{value!r}"
                )
            if self.max_length and len(str(value)) > self.max_length:
                raise ValueError(
                    f"字段 '{field_name}' 长度超限：最大长度 {self.max_length}，当前长度 {len(str(value))}，值：{value!r}"
                )

        return value

    def __repr__(self):
        return f"<Field nullable={self.nullable} type={self.field_type} default={self.default}>"