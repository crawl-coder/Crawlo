# -*- coding: UTF-8 -*-
"""
类加载器工具模块
==============
提供动态类加载功能，避免循环依赖问题。
"""
import importlib
from typing import Any


def load_class(path: str) -> Any:
    """
    动态加载类
    
    Args:
        path: 类的完整路径，如 'package.module.ClassName'
        
    Returns:
        加载的类对象
    """
    try:
        module_path, class_name = path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        raise ImportError(f"无法加载类 '{path}': {e}")