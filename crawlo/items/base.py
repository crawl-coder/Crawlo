#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Base Metaclass Definition
"""
from abc import ABCMeta
from typing import Any, Dict, Type
from .fields import Field


class ItemMeta(ABCMeta):
    """
    Metaclass for Item classes
    
    Collects all Field instances from class attributes and stores them
    in the FIELDS dictionary. Supports inheritance from parent classes.
    """
    
    def __new__(mcs, name: str, bases: tuple, attrs: Dict[str, Any]) -> Type:
        """
        Create new Item class with collected fields
        
        Args:
            mcs: Metaclass
            name: Class name
            bases: Base classes
            attrs: Class attributes
            
        Returns:
            New class instance
        """
        fields: Dict[str, Field] = {}
        
        # Inherit fields from parent classes
        for base in bases:
            if hasattr(base, 'FIELDS'):
                fields.update(base.FIELDS)
        
        # Collect fields from current class
        cls_attrs = {}
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, Field):
                fields[attr_name] = attr_value
            else:
                cls_attrs[attr_name] = attr_value
        
        # Create class instance
        cls_instance = super().__new__(mcs, name, bases, cls_attrs)
        cls_instance.FIELDS = fields
        return cls_instance
