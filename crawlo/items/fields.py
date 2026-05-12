#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Field Definition Class
"""
from typing import Any, Optional, Type


class Field:
    """
    Field definition class for defining Item field properties and validation rules
    """
    def __init__(
        self,
        nullable: bool = True,
        *,
        default: Any = None,
        field_type: Optional[Type] = None,
        max_length: Optional[int] = None,
        desc: str = ""
    ):
        self.nullable = nullable
        self.default = default
        self.field_type = field_type
        self.max_length = max_length
        self.desc = desc

    def validate(self, value: Any, field_name: str = "") -> Any:
        """
        Validate field value against rules
        
        Args:
            value: Field value to validate
            field_name: Field name for error messages
            
        Returns:
            Validated value (may be default if value is empty)
        """
        # Check if value is empty
        is_empty = value is None or (isinstance(value, str) and value.strip() == "")
        
        if is_empty:
            if self.default is not None:
                return self.default
            elif not self.nullable:
                raise ValueError(
                    f"Field '{field_name}' does not allow null or empty values."
                )
            return value
        
        # Validate non-empty value
        if self.field_type and not isinstance(value, self.field_type):
            raise TypeError(
                f"Field '{field_name}' type error: expected {self.field_type}, got {type(value)}, value: {value!r}"
            )
        
        # Check max_length for string types only
        if self.max_length and isinstance(value, str) and len(value) > self.max_length:
            raise ValueError(
                f"Field '{field_name}' length exceeded: max length {self.max_length}, current length {len(value)}, value: {value!r}"
            )

        return value

    def __repr__(self) -> str:
        return f"<Field nullable={self.nullable} type={self.field_type} default={self.default}>"