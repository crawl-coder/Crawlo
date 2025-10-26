#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置管理模块
===========
统一的配置管理接口，整合了通用配置工具、环境变量管理和大规模爬虫配置。

本模块包含：
1. ConfigUtils - 通用配置工具类
2. EnvConfigManager - 环境变量配置管理器
3. LargeScaleConfig - 大规模爬虫配置类
4. 便捷函数 - 快速访问常用配置功能
"""

import os
import re
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# 第一部分：通用配置工具
# ============================================================================

class ConfigUtils:
    """通用配置工具类"""
    
    @staticmethod
    def get_config_value(
        config_sources: List[Union[Dict, Any]], 
        key: str, 
        default: Any = None,
        value_type: type = str
    ) -> Any:
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
    
    @staticmethod
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
    
    @staticmethod
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


# ============================================================================
# 第二部分：环境变量配置管理
# ============================================================================

class EnvConfigManager:
    """环境变量配置管理器"""
    
    @staticmethod
    def get_env_var(var_name: str, default: Any = None, var_type: type = str) -> Any:
        """
        获取环境变量值
        
        Args:
            var_name: 环境变量名称
            default: 默认值
            var_type: 变量类型 (str, int, float, bool)
            
        Returns:
            环境变量值或默认值
        """
        value = os.getenv(var_name)
        if value is None:
            return default
        
        try:
            if var_type == bool:
                return value.lower() in ('1', 'true', 'yes', 'on')
            elif var_type == int:
                return int(value)
            elif var_type == float:
                return float(value)
            else:
                return value
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def get_redis_config() -> dict:
        """
        获取 Redis 配置
        
        Returns:
            Redis 配置字典
        """
        return {
            'REDIS_HOST': EnvConfigManager.get_env_var('CRAWLO_REDIS_HOST', '127.0.0.1', str),
            'REDIS_PORT': EnvConfigManager.get_env_var('CRAWLO_REDIS_PORT', 6379, int),
            'REDIS_PASSWORD': EnvConfigManager.get_env_var('CRAWLO_REDIS_PASSWORD', '', str),
            'REDIS_DB': EnvConfigManager.get_env_var('CRAWLO_REDIS_DB', 0, int),
        }
    
    @staticmethod
    def get_runtime_config() -> dict:
        """
        获取运行时配置
        
        Returns:
            运行时配置字典
        """
        return {
            'CRAWLO_MODE': EnvConfigManager.get_env_var('CRAWLO_MODE', 'standalone', str),
            'PROJECT_NAME': EnvConfigManager.get_env_var('CRAWLO_PROJECT_NAME', 'crawlo', str),
            'CONCURRENCY': EnvConfigManager.get_env_var('CRAWLO_CONCURRENCY', 8, int),
        }

    @staticmethod
    def get_version() -> str:
        """
        获取框架版本号
        
        Returns:
            框架版本号字符串
        """
        # 获取版本文件路径
        version_file = os.path.join(os.path.dirname(__file__), '..', '__version__.py')
        default_version = '1.0.0'
        
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 使用正则表达式提取版本号
                    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]*)['\"]", content)
                    if version_match:
                        return version_match.group(1)
            except Exception:
                # 如果读取失败，使用默认版本号
                pass
        
        return default_version


# ============================================================================
# 第三部分：大规模爬虫配置
# ============================================================================

class LargeScaleConfig:
    """大规模爬虫配置类"""
    
    @staticmethod
    def conservative_config(concurrency: int = 8) -> Dict[str, Any]:
        """
        保守配置 - 适用于资源有限的环境
        
        特点：
        - 较小的队列容量
        - 较低的并发数
        - 较长的延迟
        """
        from crawlo.utils.queue_helper import QueueHelper
        
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:conservative",
            max_retries=3,
            timeout=300
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 10,
            'MAX_RUNNING_SPIDERS': 1,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.2,
            'RANDOMNESS': True,
            'RANDOM_RANGE': (0.8, 1.5),
            
            # 内存控制
            'DOWNLOAD_MAXSIZE': 5 * 1024 * 1024,  # 5MB
            'CONNECTION_POOL_LIMIT': concurrency * 2,
            
            # 重试策略
            'MAX_RETRY_TIMES': 2,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.engine.Engine'
        })
        
        return config
    
    @staticmethod
    def balanced_config(concurrency: int = 16) -> Dict[str, Any]:
        """
        平衡配置 - 适用于一般生产环境
        
        特点：
        - 中等的队列容量
        - 平衡的并发数
        - 适中的延迟
        """
        from crawlo.utils.queue_helper import QueueHelper
        
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:balanced",
            max_retries=5,
            timeout=600
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 15,
            'MAX_RUNNING_SPIDERS': 2,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.1,
            'RANDOMNESS': True,
            'RANDOM_RANGE': (0.5, 1.2),
            
            # 内存控制
            'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 10MB
            'CONNECTION_POOL_LIMIT': concurrency * 3,
            
            # 重试策略
            'MAX_RETRY_TIMES': 3,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.engine.Engine'
        })
        
        return config
    
    @staticmethod
    def aggressive_config(concurrency: int = 32) -> Dict[str, Any]:
        """
        激进配置 - 适用于高性能环境
        
        特点：
        - 大的队列容量
        - 高并发数
        - 较短的延迟
        """
        from crawlo.utils.queue_helper import QueueHelper
        
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:aggressive",
            max_retries=10,
            timeout=900
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 20,
            'MAX_RUNNING_SPIDERS': 3,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.05,
            'RANDOMNESS': True,
            'RANDOM_RANGE': (0.3, 1.0),
            
            # 内存控制
            'DOWNLOAD_MAXSIZE': 20 * 1024 * 1024,  # 20MB
            'CONNECTION_POOL_LIMIT': concurrency * 4,
            
            # 重试策略
            'MAX_RETRY_TIMES': 5,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.engine.Engine'
        })
        
        return config
    
    @staticmethod
    def memory_optimized_config(concurrency: int = 12) -> Dict[str, Any]:
        """
        内存优化配置 - 适用于大规模但内存受限的场景
        
        特点：
        - 小队列，快速流转
        - 严格的内存控制
        - 使用Redis减少内存压力
        """
        from crawlo.utils.queue_helper import QueueHelper
        
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:memory_optimized",
            max_retries=3,
            timeout=300
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 5,
            'MAX_RUNNING_SPIDERS': 1,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.1,
            'RANDOMNESS': False,
            
            # 严格的内存控制
            'DOWNLOAD_MAXSIZE': 2 * 1024 * 1024,  # 2MB
            'DOWNLOAD_WARN_SIZE': 512 * 1024,     # 512KB
            'CONNECTION_POOL_LIMIT': concurrency,
            
            # 重试策略
            'MAX_RETRY_TIMES': 2,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.engine.Engine'
        })
        
        return config


def apply_large_scale_config(
    settings_dict: Dict[str, Any], 
    config_type: str = "balanced", 
    concurrency: Optional[int] = None
):
    """
    应用大规模配置
    
    Args:
        settings_dict: 设置字典
        config_type: 配置类型 ("conservative", "balanced", "aggressive", "memory_optimized")
        concurrency: 并发数（可选，不指定则使用默认值）
    """
    config_map = {
        "conservative": LargeScaleConfig.conservative_config,
        "balanced": LargeScaleConfig.balanced_config,
        "aggressive": LargeScaleConfig.aggressive_config,
        "memory_optimized": LargeScaleConfig.memory_optimized_config
    }
    
    if config_type not in config_map:
        raise ValueError(f"不支持的配置类型: {config_type}")
    
    if concurrency:
        config = config_map[config_type](concurrency)
    else:
        config = config_map[config_type]()
    
    settings_dict.update(config)
    
    return config


# 导出所有公共API
__all__ = [
    'ConfigUtils',
    'EnvConfigManager',
    'LargeScaleConfig',
    'apply_large_scale_config',
]
