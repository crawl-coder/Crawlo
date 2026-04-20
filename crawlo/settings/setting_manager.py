#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置管理器
==========
提供统一的配置管理，支持多种配置格式并保持向后兼容。

配置格式优先级：
1. 字典格式（推荐）: {'path.to.Middleware': 500}
2. 元组列表格式: [('path.to.Middleware', 500)]
3. 简单列表格式: ['path.to.Middleware'] (默认优先级 0)

使用示例：
    # 推荐格式
    MIDDLEWARES = {
        'myproject.middlewares.CustomMiddleware': 500
    }
    
    # 使用优先级常量
    from crawlo.utils import MiddlewarePriority
    MIDDLEWARES = {
        'myproject.middlewares.CustomMiddleware': MiddlewarePriority.CUSTOM
    }
"""
import json
from copy import deepcopy
from importlib import import_module
from collections.abc import MutableMapping
from typing import Any, Dict, List, Optional, Union, Type
from enum import Enum

from crawlo.settings import default_settings


class ConfigFormat:
    """配置格式类型"""
    DICT = 'dict'      # 字典格式 {'path': priority}
    LIST = 'list'      # 列表格式 ['path']
    TUPLE_LIST = 'tuple_list'  # 元组列表 [('path', priority)]


def normalize_component_config(
    config: Union[Dict, List, tuple, None],
    default_priority: int = 500
) -> Dict[str, int]:
    """
    将组件配置标准化为字典格式
    
    Args:
        config: 组件配置（字典/列表/元组列表）
        default_priority: 默认优先级（500 表示中等优先级，适合管道）
        
    Returns:
        Dict[str, int]: 标准化后的字典 {path: priority}
    """
    if not config:
        return {}
    
    if isinstance(config, dict):
        return {k: v for k, v in config.items() if k and not str(k).strip().startswith('#')}
    
    if isinstance(config, tuple):
        config = [config]
    
    if isinstance(config, (list, tuple)):
        result = {}
        for item in config:
            if not item:
                continue
            if isinstance(item, str):
                if item.strip() and not item.strip().startswith('#'):
                    result[item.strip()] = default_priority
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                path = str(item[0]).strip()
                if path and not path.startswith('#'):
                    try:
                        priority = int(item[1])
                    except (ValueError, TypeError):
                        priority = default_priority
                    result[path] = priority
        return result
    
    return {}


def merge_component_configs(
    default: Dict[str, int],
    user: Dict[str, int]
) -> Dict[str, int]:
    """
    合并组件配置
    
    用户配置覆盖默认配置。
    
    Args:
        default: 默认配置
        user: 用户配置
        
    Returns:
        Dict[str, int]: 合并后的配置
    """
    result = default.copy()
    result.update(user)
    return result


class SettingManager(MutableMapping):
    """
    配置管理器
    
    提供统一的配置访问和修改接口，支持多种配置格式。
    
    特性：
    - 支持多种配置格式自动转换
    - 支持配置优先级合并
    - 支持动态配置处理
    - 向后兼容旧格式
    """
    
    # 特殊配置键，需要特殊合并逻辑
    _COMPONENT_KEYS = frozenset(['MIDDLEWARES', 'PIPELINES', 'EXTENSIONS'])
    
    # 去重管道列表
    _DEDUP_PIPELINES = frozenset([
        'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
        'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
    ])
    
    def __init__(self, values: Optional[Dict[str, Any]] = None):
        """
        初始化配置管理器
        
        Args:
            values: 初始配置字典
        """
        self.attributes: Dict[str, Any] = {}
        self.set_settings(default_settings)
        self._merge_config(values)
        self._process_dynamic_config()
    
    def _merge_config(self, user_config: Optional[Dict[str, Any]]) -> None:
        """
        合并用户配置
        
        Args:
            user_config: 用户配置字典
        """
        if not user_config:
            return
        
        # 处理组件配置（中间件、管道、扩展）
        for key in self._COMPONENT_KEYS:
            if key in user_config:
                self._merge_component_config(key, user_config[key])
        
        # 处理其他配置
        for key, value in user_config.items():
            if key not in self._COMPONENT_KEYS:
                self.attributes[key] = value
        
        # 特殊处理：确保去重管道在最前面
        self._ensure_dedup_pipeline()
    
    def _merge_component_config(
        self, 
        key: str, 
        user_config: Union[Dict, List, tuple]
    ) -> None:
        """
        合并组件配置
            
        Args:
            key: 配置键名
            user_config: 用户配置
        """
        # 标准化用户配置
        user_normalized = normalize_component_config(user_config)
    
        # 获取默认配置并标准化
        default_config = self.attributes.get(key, {})
        default_normalized = normalize_component_config(default_config)
    
        # 合并配置
        merged = merge_component_configs(default_normalized, user_normalized)
    
        # 存储为字典格式（保留优先级）
        self.attributes[key] = merged
    
    def _ensure_dedup_pipeline(self) -> None:
        """确保去重管道在管道列表最前面（优先级最高，数字最小）"""
        dedup_pipeline = self.attributes.get('DEFAULT_DEDUP_PIPELINE')
        if not dedup_pipeline:
            return
        
        pipelines = self.attributes.get('PIPELINES', {})
        
        # 确保是字典格式
        if isinstance(pipelines, (list, tuple)):
            # 从列表转换为字典，默认优先级 500
            pipelines = {p: 500 + i for i, p in enumerate(pipelines) if isinstance(p, str)}
        
        # 移除已有的去重管道
        pipelines = {k: v for k, v in pipelines.items() if k not in self._DEDUP_PIPELINES}
        
        # 在开头插入指定的去重管道（优先级最高：数字最小）
        if dedup_pipeline not in pipelines:
            # 找到当前最小的优先级
            min_priority = min(pipelines.values()) if pipelines else 100
            # 去重管道优先级必须比所有其他管道都小，确保最先执行
            pipelines[dedup_pipeline] = max(1, min_priority - 100)
        
        self.attributes['PIPELINES'] = pipelines
    
    def set_settings(self, module: Union[str, object]) -> None:
        """
        从模块加载配置
        
        Args:
            module: 模块对象或模块路径字符串
        """
        if isinstance(module, str):
            module = import_module(module)
        
        # 收集模块中的所有配置项
        module_settings = {}
        for key in dir(module):
            if key.isupper():
                module_settings[key] = getattr(module, key)
        
        self._merge_config(module_settings)
        self._process_dynamic_config()
    
    def _process_dynamic_config(self) -> None:
        """处理动态配置项"""
        if self.attributes.get('LOG_FILE') is None:
            project_name = self.attributes.get('PROJECT_NAME', 'crawlo')
            self.attributes['LOG_FILE'] = f'logs/{project_name}.log'
    
    # ==================== 配置获取方法 ====================
    
    # 哨兵值：用于区分"未设置"和"显式设置为 None"
    _SENTINEL = object()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值（仅在键不存在时使用，显式设置为 None 的键返回 None）
            
        Returns:
            配置值。如果键存在则返回对应值（包括 None），不存在时返回 default。
        """
        if key in self.attributes:
            return self.attributes[key]
        return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置值"""
        return int(self.get(key, default=default))
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置值"""
        return float(self.get(key, default=default))
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置值"""
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
    
    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """获取列表配置值"""
        values = self.get(key, default or [])
        if isinstance(values, str):
            return [v.strip() for v in values.split(',') if v.strip()]
        try:
            return list(values)
        except TypeError:
            return [values]
    
    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """获取字典配置值"""
        value = self.get(key, default or {})
        if isinstance(value, str):
            value = json.loads(value)
        try:
            return dict(value)
        except TypeError:
            return value
    
    def get_enum(self, key: str, enum_class: Type[Enum], default: Enum = None) -> Enum:
        """
        获取枚举配置值
        
        Args:
            key: 配置键名
            enum_class: 枚举类
            default: 默认值
            
        Returns:
            Enum: 枚举值
            
        Raises:
            ValueError: 如果值无法转换为枚举
        """
        value = self.get(key)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"配置项 '{key}' 不存在，且未提供默认值")
        
        # 如果已经是枚举类型，直接返回
        if isinstance(value, enum_class):
            return value
        
        # 尝试从字符串或整数转换
        try:
            # 优先尝试按名称查找
            if isinstance(value, str):
                try:
                    return enum_class[value.upper()]
                except KeyError:
                    pass
            # 然后尝试按值查找
            return enum_class(value)
        except (ValueError, KeyError) as e:
            raise ValueError(
                f"无法将配置值 '{value}' 转换为枚举 {enum_class.__name__}"
            ) from e
    
    # ==================== 配置设置方法 ====================
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键名
            value: 配置值
        """
        self.attributes[key] = value
    
    def setdefault(self, key: str, default: Any = None) -> Any:
        """
        如果键不存在则设置默认值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        if key not in self.attributes:
            self.attributes[key] = default
        return self.attributes[key]
    
    def update(self, other: Dict[str, Any]) -> None:
        """
        批量更新配置
        
        Args:
            other: 配置字典
        """
        self._merge_config(other)
    
    def update_attributes(self, attributes: Optional[Dict[str, Any]]) -> None:
        """
        批量更新配置（兼容旧接口）
        
        Args:
            attributes: 配置字典
        """
        if attributes:
            self.update(attributes)
    
    # ==================== 实现 MutableMapping 接口 ====================
    
    def __getitem__(self, key: str) -> Any:
        return self.attributes[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)
    
    def __delitem__(self, key: str) -> None:
        del self.attributes[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self.attributes
    
    def __iter__(self):
        return iter(self.attributes)
    
    def __len__(self) -> int:
        return len(self.attributes)
    
    def __str__(self) -> str:
        return f'<Settings: {len(self.attributes)} items>'
    
    __repr__ = __str__
    
    # ==================== 复制和序列化 ====================
    
    def copy(self) -> 'SettingManager':
        """创建配置的深拷贝"""
        return deepcopy(self)
    
    def __deepcopy__(self, memo: dict) -> 'SettingManager':
        """自定义深拷贝，跳过不可序列化的对象"""
        cls = self.__class__
        new_instance = cls.__new__(cls)
        
        new_attributes = {}
        for key, value in self.attributes.items():
            try:
                new_attributes[key] = deepcopy(value, memo)
            except Exception:
                new_attributes[key] = value
        
        new_instance.attributes = new_attributes
        return new_instance
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 配置字典的副本
        """
        return dict(self.attributes)
    
    # ==================== 工具方法 ====================
    
    def get_component_priority(
        self, 
        component_key: str, 
        component_path: str
    ) -> int:
        """
        获取组件优先级
        
        Args:
            component_key: 组件配置键（MIDDLEWARES/PIPELINES/EXTENSIONS）
            component_path: 组件路径
            
        Returns:
            int: 优先级，不存在时返回 0
        """
        config = self.attributes.get(component_key, {})
        normalized = normalize_component_config(config)
        return normalized.get(component_path, 0)
    
    def set_component_priority(
        self, 
        component_key: str, 
        component_path: str, 
        priority: int
    ) -> None:
        """
        设置组件优先级
        
        Args:
            component_key: 组件配置键
            component_path: 组件路径
            priority: 优先级
        """
        config = self.attributes.get(component_key, {})
        normalized = normalize_component_config(config)
        normalized[component_path] = priority
        self.attributes[component_key] = normalized
