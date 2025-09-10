#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
环境变量配置工具
提供统一的环境变量读取和配置管理机制
"""
import os
from typing import Optional, Union, Any


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
            'REDIS_HOST': EnvConfigManager.get_env_var('REDIS_HOST', '127.0.0.1', str),
            'REDIS_PORT': EnvConfigManager.get_env_var('REDIS_PORT', 6379, int),
            'REDIS_PASSWORD': EnvConfigManager.get_env_var('REDIS_PASSWORD', '', str),
            'REDIS_DB': EnvConfigManager.get_env_var('REDIS_DB', 0, int),
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
            'PROJECT_NAME': EnvConfigManager.get_env_var('PROJECT_NAME', 'crawlo', str),
            'CONCURRENCY': EnvConfigManager.get_env_var('CONCURRENCY', 8, int),
        }


# 便捷函数
def get_env_var(var_name: str, default: Any = None, var_type: type = str) -> Any:
    """
    便捷函数：获取环境变量值
    
    Args:
        var_name: 环境变量名称
        default: 默认值
        var_type: 变量类型 (str, int, float, bool)
        
    Returns:
        环境变量值或默认值
    """
    return EnvConfigManager.get_env_var(var_name, default, var_type)


def get_redis_config() -> dict:
    """
    便捷函数：获取 Redis 配置
    
    Returns:
        Redis 配置字典
    """
    return EnvConfigManager.get_redis_config()


def get_runtime_config() -> dict:
    """
    便捷函数：获取运行时配置
    
    Returns:
        运行时配置字典
    """
    return EnvConfigManager.get_runtime_config()