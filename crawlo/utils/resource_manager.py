#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
资源管理器 - 统一管理所有可清理资源
========================================

功能特性：
- 统一注册和清理资源
- 支持异步资源清理
- 资源泄露检测
- 清理顺序保证（LIFO）
"""
import asyncio
import time
import traceback
from typing import Any, Callable, List, Tuple, Optional, Dict
from enum import Enum

from crawlo.logging import get_logger


class ResourceType(Enum):
    """资源类型枚举"""
    DOWNLOADER = "downloader"
    REDIS_POOL = "redis_pool"
    QUEUE = "queue"
    FILTER = "filter"
    PIPELINE = "pipeline"
    MIDDLEWARE = "middleware"
    EXTENSION = "extension"
    SESSION = "session"
    BROWSER = "browser"
    OTHER = "other"


class ResourceStatus(Enum):
    """资源状态"""
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class ManagedResource:
    """托管资源"""
    
    def __init__(self, 
                 resource: Any,
                 cleanup_func: Callable,
                 resource_type: ResourceType = ResourceType.OTHER,
                 name: Optional[str] = None):
        self.resource = resource
        self.cleanup_func = cleanup_func
        self.resource_type = resource_type
        self.name = name or f"{resource_type.value}_{id(resource)}"
        self.status = ResourceStatus.ACTIVE
        self.created_at = time.time()
        self.closed_at: Optional[float] = None
    
    async def cleanup(self) -> bool:
        """清理资源"""
        if self.status == ResourceStatus.CLOSED:
            return True
        
        self.status = ResourceStatus.CLOSING
        try:
            # 检查cleanup_func是否为异步函数
            if asyncio.iscoroutinefunction(self.cleanup_func):
                await self.cleanup_func(self.resource)
            else:
                # 同步函数，直接调用
                result = self.cleanup_func(self.resource)
                # 如果返回的是协程，则await
                if asyncio.iscoroutine(result):
                    await result
            
            self.status = ResourceStatus.CLOSED
            self.closed_at = time.time()
            return True
        except Exception as e:
            self.status = ResourceStatus.ERROR
            raise e
    
    def get_lifetime(self) -> float:
        """获取资源生命周期（秒）"""
        end_time = self.closed_at or time.time()
        return end_time - self.created_at


class ResourceManager:
    """
    资源管理器 - 统一管理所有可清理资源
    
    特性：
    1. 自动跟踪注册的资源
    2. 保证清理顺序（LIFO - 后进先出）
    3. 容错清理（一个失败不影响其他）
    4. 资源泄露检测
    5. 统计和监控
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._resources: List[ManagedResource] = []
        self._lock = asyncio.Lock()
        self._cleanup_errors: List[Tuple[str, Exception]] = []
        self._logger = get_logger(f"ResourceManager.{name}")
        
        # 统计信息
        self._stats = {
            'total_registered': 0,
            'total_cleaned': 0,
            'total_errors': 0,
            'active_resources': 0,
        }
    
    def register(self,
                 resource: Any,
                 cleanup_func: Callable,
                 resource_type: ResourceType = ResourceType.OTHER,
                 name: Optional[str] = None) -> ManagedResource:
        """
        注册需要清理的资源
        
        Args:
            resource: 资源对象
            cleanup_func: 清理函数（同步或异步）
            resource_type: 资源类型
            name: 资源名称（用于日志）
        
        Returns:
            托管资源对象
        """
        managed = ManagedResource(resource, cleanup_func, resource_type, name)
        self._resources.append(managed)
        self._stats['total_registered'] += 1
        self._stats['active_resources'] += 1
        
        self._logger.debug(f"Resource registered: {managed.name} ({resource_type.value})")
        return managed
    
    async def cleanup_all(self, reverse: bool = True) -> Dict[str, Any]:
        """
        清理所有注册的资源
        
        Args:
            reverse: 是否反向清理（LIFO，推荐）
        
        Returns:
            清理结果统计
        """
        async with self._lock:
            if not self._resources:
                self._logger.debug("No resources to cleanup")
                return self._get_cleanup_stats()
            
            self._logger.info(f"Starting cleanup of {len(self._resources)} resources...")
            
            # 反向清理（后创建的先清理）
            resources = reversed(self._resources) if reverse else self._resources
            
            cleanup_start = time.time()
            success_count = 0
            error_count = 0
            
            for managed in resources:
                try:
                    self._logger.debug(f"Cleaning up: {managed.name}")
                    await managed.cleanup()
                    success_count += 1
                    self._stats['total_cleaned'] += 1
                    self._stats['active_resources'] -= 1
                except Exception as e:
                    error_count += 1
                    self._stats['total_errors'] += 1
                    self._cleanup_errors.append((managed.name, e))
                    self._logger.error(
                        f"Failed to cleanup {managed.name}: {e}",
                        exc_info=True
                    )
                    # 继续清理其他资源，不中断
            
            cleanup_duration = time.time() - cleanup_start
            
            # 清空资源列表
            cleaned_count = len(self._resources)
            self._resources.clear()
            
            result = {
                'success': success_count,
                'errors': error_count,
                'duration': cleanup_duration,
                'total_resources': success_count + error_count,
                'cleaned_resources': cleaned_count
            }
            
            if error_count > 0:
                self._logger.warning(
                    f"Cleanup completed with errors: {success_count} success, "
                    f"{error_count} errors in {cleanup_duration:.2f}s"
                )
            else:
                self._logger.info(
                    f"Cleanup completed successfully: {success_count} resources "
                    f"in {cleanup_duration:.2f}s"
                )
            
            return result
    
    async def cleanup_by_type(self, resource_type: ResourceType) -> int:
        """
        按类型清理资源
        
        Args:
            resource_type: 资源类型
        
        Returns:
            清理的资源数量
        """
        async with self._lock:
            to_cleanup = [r for r in self._resources if r.resource_type == resource_type]
            
            if not to_cleanup:
                return 0
            
            cleaned = 0
            for managed in reversed(to_cleanup):
                try:
                    await managed.cleanup()
                    self._resources.remove(managed)
                    cleaned += 1
                    self._stats['total_cleaned'] += 1
                    self._stats['active_resources'] -= 1
                except Exception as e:
                    self._logger.error(f"Failed to cleanup {managed.name}: {e}")
                    self._stats['total_errors'] += 1
            
            return cleaned
    
    def get_active_resources(self) -> List[ManagedResource]:
        """获取所有活跃资源"""
        return [r for r in self._resources if r.status == ResourceStatus.ACTIVE]
    
    def get_resources_by_type(self, resource_type: ResourceType) -> List[ManagedResource]:
        """按类型获取资源"""
        return [r for r in self._resources if r.resource_type == resource_type]
    
    def detect_leaks(self, max_lifetime: float = 3600) -> List[ManagedResource]:
        """
        检测可能的资源泄露
        
        Args:
            max_lifetime: 最大生命周期（秒），超过此时间未清理视为泄露
        
        Returns:
            可能泄露的资源列表
        """
        current_time = time.time()
        leaks = []
        
        for managed in self._resources:
            if managed.status == ResourceStatus.ACTIVE:
                lifetime = current_time - managed.created_at
                if lifetime > max_lifetime:
                    leaks.append(managed)
                    self._logger.warning(
                        f"Potential leak detected: {managed.name} "
                        f"(lifetime: {lifetime:.2f}s)"
                    )
        
        return leaks
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            'cleanup_errors': len(self._cleanup_errors),
            'active_by_type': self._get_active_by_type(),
        }
    
    def _get_active_by_type(self) -> Dict[str, int]:
        """按类型统计活跃资源"""
        result = {}
        for managed in self._resources:
            if managed.status == ResourceStatus.ACTIVE:
                type_name = managed.resource_type.value
                result[type_name] = result.get(type_name, 0) + 1
        return result
    
    def _get_cleanup_stats(self) -> Dict[str, Any]:
        """获取清理统计"""
        return {
            'success': 0,
            'errors': 0,
            'duration': 0.0,
            'total_resources': 0,
        }
    
    async def __aenter__(self):
        """上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，自动清理"""
        await self.cleanup_all()
        return False


# 全局资源管理器注册表
_global_managers: Dict[str, ResourceManager] = {}


def get_resource_manager(name: str = "default") -> ResourceManager:
    """
    获取资源管理器实例（单例）
    
    Args:
        name: 管理器名称
    
    Returns:
        资源管理器实例
    """
    if name not in _global_managers:
        _global_managers[name] = ResourceManager(name)
    return _global_managers[name]


async def cleanup_all_managers():
    """清理所有资源管理器"""
    logger = get_logger("ResourceManager")
    
    for name, manager in _global_managers.items():
        try:
            logger.info(f"Cleaning up resource manager: {name}")
            await manager.cleanup_all()
        except Exception as e:
            logger.error(f"Failed to cleanup manager {name}: {e}")
    
    _global_managers.clear()
