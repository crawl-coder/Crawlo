#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
应用上下文管理器
================
提供上下文隔离机制，替代全局变量的部分功能

问题背景：
框架使用多个全局变量，导致：
- 多实例冲突
- 测试隔离困难
- 内存泄漏风险

解决方案：
1. 提供 reset 函数用于测试清理
2. 提供 ApplicationContext 用于新代码的上下文隔离
3. 保持向后兼容
"""
import asyncio
import uuid
from typing import Dict, Type, Optional, Set, Any
from dataclasses import dataclass, field


@dataclass
class ApplicationContext:
    """
    应用上下文容器
    
    持有所有框架组件的单例引用，支持上下文隔离
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 爬虫注册表
    spider_registry: Dict[str, Type['Spider']] = field(default_factory=dict)
    
    # 组件注册表
    component_registry: Optional['ComponentRegistry'] = None
    
    # 框架实例
    framework: Optional['CrawloFramework'] = None
    
    # 资源追踪
    resources: Set[Any] = field(default_factory=set)
    
    # 爬虫实例
    crawlers: Dict[str, Any] = field(default_factory=dict)
    
    def register_spider(self, name: str, spider_cls: Type['Spider']):
        """注册爬虫"""
        if name in self.spider_registry:
            raise ValueError(f"Spider '{name}' already registered")
        self.spider_registry[name] = spider_cls
    
    def get_spider(self, name: str) -> Optional[Type['Spider']]:
        """获取爬虫类"""
        return self.spider_registry.get(name)
    
    def unregister_spider(self, name: str) -> bool:
        """取消注册爬虫"""
        if name in self.spider_registry:
            del self.spider_registry[name]
            return True
        return False
    
    def add_resource(self, resource: Any):
        """添加资源追踪"""
        self.resources.add(resource)
    
    def remove_resource(self, resource: Any) -> bool:
        """移除资源追踪"""
        if resource in self.resources:
            self.resources.discard(resource)
            return True
        return False
    
    async def cleanup(self):
        """清理上下文资源"""
        for resource in list(self.resources):
            try:
                if hasattr(resource, 'close'):
                    close_method = resource.close
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
                elif hasattr(resource, 'cleanup'):
                    cleanup_method = resource.cleanup
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()
            except Exception as e:
                print(f"Error cleaning up resource: {e}")
        
        self.resources.clear()
        self.spider_registry.clear()
        self.crawlers.clear()


# 全局上下文持有者
_global_context: Optional[ApplicationContext] = None


def get_global_context() -> ApplicationContext:
    """
    获取全局上下文
    
    Returns:
        ApplicationContext: 全局上下文实例
    """
    global _global_context
    if _global_context is None:
        _global_context = ApplicationContext()
    return _global_context


def reset_global_context():
    """
    重置全局上下文
    
    用于测试隔离和内存清理
    """
    global _global_context
    _global_context = None


def set_global_context(ctx: ApplicationContext):
    """
    设置全局上下文
    
    Args:
        ctx: 上下文实例
    """
    global _global_context
    _global_context = ctx


async def create_context() -> ApplicationContext:
    """
    创建新的隔离上下文
    
    Returns:
        ApplicationContext: 新上下文
    """
    ctx = ApplicationContext()
    set_global_context(ctx)
    return ctx
