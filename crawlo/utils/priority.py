#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
中间件优先级定义
================
提供语义化的中间件优先级常量，便于用户理解和配置。

优先级规则：
- 数值越小，请求阶段越先执行
- 数值越大，响应阶段越先执行
- 先进后出（LIFO）模式

使用示例：
    # 使用预设优先级
    MIDDLEWARES = {
        'myproject.middlewares.CustomMiddleware': MiddlewarePriority.CUSTOM,
    }
"""
from enum import IntEnum
from typing import Dict, List, Tuple


class MiddlewarePriority(IntEnum):
    """
    中间件优先级枚举
    
    数值规则：
    - 请求阶段：数值小的先执行
    - 响应阶段：数值大的先执行
    """
    # 自定义中间件默认位置
    CUSTOM = 500
    
    # 自定义请求处理
    CUSTOM_REQUEST = 450
    
    # 自定义响应处理
    CUSTOM_RESPONSE = 550


class MiddlewarePriorityGroup:
    """
    中间件优先级分组
    
    提供按功能分组的中间件配置方式，便于管理。
    
    使用示例：
        config = MiddlewarePriorityGroup()
        config.add_request('myproject.middlewares.AuthMiddleware', 250)
        config.add_response('myproject.middlewares.ParseMiddleware', 650)
        MIDDLEWARES = config.to_dict()
    """
    
    def __init__(self):
        self._middlewares: Dict[str, int] = {}
    
    def add(self, middleware_path: str, priority: int) -> 'MiddlewarePriorityGroup':
        """添加中间件"""
        self._middlewares[middleware_path] = priority
        return self
    
    def add_request(
        self, 
        middleware_path: str, 
        priority: int = MiddlewarePriority.CUSTOM_REQUEST
    ) -> 'MiddlewarePriorityGroup':
        """添加请求阶段中间件"""
        return self.add(middleware_path, priority)
    
    def add_response(
        self, 
        middleware_path: str, 
        priority: int = MiddlewarePriority.CUSTOM_RESPONSE
    ) -> 'MiddlewarePriorityGroup':
        """添加响应阶段中间件"""
        return self.add(middleware_path, priority)
    
    def remove(self, middleware_path: str) -> 'MiddlewarePriorityGroup':
        """移除中间件"""
        self._middlewares.pop(middleware_path, None)
        return self
    
    def to_dict(self) -> Dict[str, int]:
        """转换为字典格式"""
        return dict(sorted(self._middlewares.items(), key=lambda x: x[1]))
    
    def to_list(self) -> List[Tuple[str, int]]:
        """转换为列表格式（按优先级排序）"""
        return sorted(self._middlewares.items(), key=lambda x: x[1])


# ==================== 框架内置中间件默认优先级 ====================
# 与 default_settings.py 中的配置保持一致

BUILTIN_MIDDLEWARE_PRIORITIES = {
    # 请求预处理阶段（数值小→请求先执行）
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware': 100,
    'crawlo.middleware.download_delay.DownloadDelayMiddleware': 200,
    'crawlo.middleware.default_header.DefaultHeaderMiddleware': 300,
    'crawlo.middleware.offsite.OffsiteMiddleware': 400,
    
    # 响应处理阶段（数值大→响应先执行）
    'crawlo.middleware.response_filter.ResponseFilterMiddleware': 700,
    'crawlo.middleware.response_code.ResponseCodeMiddleware': 650,
    'crawlo.middleware.retry.RetryMiddleware': 600,
}


def get_default_middleware_priority(middleware_path: str) -> int:
    """
    获取内置中间件的默认优先级
    
    Args:
        middleware_path: 中间件路径
        
    Returns:
        int: 默认优先级，未找到时返回 CUSTOM (500)
    """
    return BUILTIN_MIDDLEWARE_PRIORITIES.get(middleware_path, MiddlewarePriority.CUSTOM)


# ==================== 导出 ====================

__all__ = [
    'MiddlewarePriority',
    'MiddlewarePriorityGroup',
    'BUILTIN_MIDDLEWARE_PRIORITIES',
    'get_default_middleware_priority',
]
