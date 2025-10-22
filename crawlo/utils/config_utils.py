#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置工具模块 - 提供通用的配置获取和处理功能
"""

from typing import Any, Dict, List, Optional, Union
import os


def get_config_value(config_sources: List[Union[Dict, Any]], 
                    key: str, 
                    default: Any = None,
                    value_type: type = str) -> Any:
    """
    从多个配置源中获取配置值
    
    Args:
        config_sources: 配置源列表，按优先级排序
        key: 配置键名
        default: 默认值
        value_type: 值类型
        
    Returns:
        配置值或默认值
    """
    for config_source in config_sources:
        if not config_source:
            continue
            
        # 获取配置值
        value = None
        if hasattr(config_source, 'get'):
            value = config_source.get(key)
        elif hasattr(config_source, key):
            value = getattr(config_source, key)
        else:
            continue
            
        if value is not None:
            # 类型转换
            try:
                if value_type == bool:
                    if isinstance(value, str):
                        return value.lower() in ('1', 'true', 'yes', 'on')
                    return bool(value)
                elif value_type == int:
                    return int(value)
                elif value_type == float:
                    return float(value)
                else:
                    return value_type(value)
            except (ValueError, TypeError):
                continue
    
    return default


def has_config_prefix(config_source: Union[Dict, Any], prefix: str) -> bool:
    """
    检查配置源是否包含指定前缀的配置项
    
    Args:
        config_source: 配置源
        prefix: 前缀
        
    Returns:
        是否包含指定前缀的配置项
    """
    if not config_source:
        return False
        
    if hasattr(config_source, 'keys'):
        return any(key.startswith(prefix) for key in config_source.keys())
    elif hasattr(config_source, '__dict__'):
        return any(key.startswith(prefix) for key in config_source.__dict__.keys())
    else:
        return any(key.startswith(prefix) for key in dir(config_source))


def merge_config_sources(config_sources: List[Union[Dict, Any]]) -> Dict[str, Any]:
    """
    合并多个配置源，后面的配置源优先级更高
    
    Args:
        config_sources: 配置源列表
        
    Returns:
        合并后的配置字典
    """
    merged_config = {}
    
    for config_source in config_sources:
        if not config_source:
            continue
            
        if hasattr(config_source, 'keys'):
            # 字典类型配置源
            for key, value in config_source.items():
                if key.isupper():  # 只合并大写的配置项
                    merged_config[key] = value
        elif hasattr(config_source, '__dict__'):
            # 对象类型配置源
            for key, value in config_source.__dict__.items():
                if key.isupper():
                    merged_config[key] = value
        else:
            # 其他类型配置源
            for key in dir(config_source):
                if key.isupper():
                    merged_config[key] = getattr(config_source, key)
    
    return merged_config