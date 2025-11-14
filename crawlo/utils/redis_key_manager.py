#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis Key 管理器
================
统一管理 Crawlo 框架中所有 Redis Key 的生成和验证
"""
from typing import Optional, Any

from crawlo.logging import get_logger
from crawlo.utils.redis_manager import validate_redis_key_naming


class RedisKeyManager:
    """Redis Key 管理器"""
    
    def __init__(self, project_name: str = "default", spider_name: Optional[str] = None):
        """
        初始化 Redis Key 管理器
        
        Args:
            project_name: 项目名称
            spider_name: 爬虫名称（可选）
        """
        self.project_name = project_name
        self.spider_name = spider_name
        self.logger = get_logger(self.__class__.__name__)
        
        # 如果提供了 spider_name，则使用更细粒度的命名空间
        if self.spider_name:
            self.namespace = f"{self.project_name}:{self.spider_name}"
        else:
            self.namespace = self.project_name
    
    def set_spider_name(self, spider_name: str) -> None:
        """
        设置爬虫名称
        
        Args:
            spider_name: 爬虫名称
        """
        self.spider_name = spider_name if spider_name else None
        # 更新命名空间
        if self.spider_name:
            self.namespace = f"{self.project_name}:{self.spider_name}"
        else:
            self.namespace = self.project_name
    
    def _generate_key(self, component: str, sub_component: str) -> str:
        """
        生成 Redis Key
        
        Args:
            component: 组件类型 (queue, filter, item)
            sub_component: 子组件类型
            
        Returns:
            str: 生成的 Redis Key
        """
        key = f"crawlo:{self.namespace}:{component}:{sub_component}"
        
        # 验证生成的 key 是否符合规范
        if not validate_redis_key_naming(key, self.project_name):
            self.logger.warning(f"生成的 Redis Key 不符合命名规范: {key}")
        
        return key
    
    # ==================== 队列相关 Key ====================
    
    def get_requests_queue_key(self) -> str:
        """获取请求队列 Key"""
        return self._generate_key("queue", "requests")
    
    def get_processing_queue_key(self) -> str:
        """获取处理中队列 Key"""
        return self._generate_key("queue", "processing")
    
    def get_failed_queue_key(self) -> str:
        """获取失败队列 Key"""
        return self._generate_key("queue", "failed")
    
    def get_requests_data_key(self) -> str:
        """获取请求数据 Hash Key"""
        return f"{self.get_requests_queue_key()}:data"
    
    def get_processing_data_key(self) -> str:
        """获取处理中数据 Hash Key"""
        return f"{self.get_processing_queue_key()}:data"
    
    def get_failed_retries_key(self, request_key: str) -> str:
        """获取失败重试计数 Key"""
        return f"{self.get_failed_queue_key()}:retries:{request_key}"
    
    # ==================== 过滤器相关 Key ====================
    
    def get_filter_fingerprint_key(self) -> str:
        """获取请求去重过滤器指纹 Key"""
        return self._generate_key("filter", "fingerprint")
    
    # ==================== 数据项相关 Key ====================
    
    def get_item_fingerprint_key(self) -> str:
        """获取数据项去重指纹 Key"""
        return self._generate_key("item", "fingerprint")
    
    # ==================== 静态方法 ====================
    
    @staticmethod
    def from_settings(settings: Any) -> 'RedisKeyManager':
        """
        从配置创建 Redis Key 管理器实例
        
        Args:
            settings: 配置对象
            
        Returns:
            RedisKeyManager: Redis Key 管理器实例
        """
        # 安全获取配置值
        project_name = getattr(settings, 'get', lambda k, d: getattr(settings, k, d))(
            'PROJECT_NAME', 'default'
        )
        
        # 尝试获取 spider_name，这通常在运行时才能确定
        spider_name = getattr(settings, 'get', lambda k, d: getattr(settings, k, d))(
            'SPIDER_NAME', None
        )
        
        return RedisKeyManager(project_name, spider_name)
    
    # ==================== Key 信息提取 ====================
    
    @staticmethod
    def extract_project_name_from_key(key: str) -> Optional[str]:
        """
        从 Redis Key 中提取项目名称
        
        Args:
            key: Redis Key
            
        Returns:
            Optional[str]: 项目名称
        """
        if not key or not key.startswith('crawlo:'):
            return None
            
        parts = key.split(':')
        if len(parts) >= 2:
            return parts[1]
        return None
    
    @staticmethod
    def extract_spider_name_from_key(key: str) -> Optional[str]:
        """
        从 Redis Key 中提取爬虫名称
        
        Args:
            key: Redis Key
            
        Returns:
            Optional[str]: 爬虫名称
        """
        if not key or not key.startswith('crawlo:'):
            return None
            
        parts = key.split(':')
        # 如果格式是 crawlo:project:spider:component:sub_component
        if len(parts) >= 4:
            # 检查是否存在 spider 部分
            if parts[2] not in ['queue', 'filter', 'item']:
                return parts[2]
        return None


# 便利函数
def create_redis_key_manager(project_name: str = "default", spider_name: Optional[str] = None) -> RedisKeyManager:
    """
    创建 Redis Key 管理器实例（便利函数）
    
    Args:
        project_name: 项目名称
        spider_name: 爬虫名称（可选）
        
    Returns:
        RedisKeyManager: Redis Key 管理器实例
    """
    return RedisKeyManager(project_name, spider_name)


def get_redis_key_manager_from_settings(settings: Any) -> RedisKeyManager:
    """
    从配置创建 Redis Key 管理器实例（便利函数）
    
    Args:
        settings: 配置对象
        
    Returns:
        RedisKeyManager: Redis Key 管理器实例
    """
    return RedisKeyManager.from_settings(settings)