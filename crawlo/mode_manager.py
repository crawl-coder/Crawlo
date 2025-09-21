#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
运行模式管理器
==============
管理 Crawlo 框架的不同运行模式，提供优雅的配置方式。

支持的运行模式：
1. standalone - 单机模式（默认）
2. distributed - 分布式模式  
3. auto - 自动检测模式
"""
import os
from enum import Enum
from typing import Dict, Any, Optional

from crawlo.utils.log import get_logger


class RunMode(Enum):
    """运行模式枚举"""
    STANDALONE = "standalone"    # 单机模式
    DISTRIBUTED = "distributed"  # 分布式模式
    AUTO = "auto"               # 自动检测模式


class ModeManager:
    """运行模式管理器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    @staticmethod
    def get_standalone_settings() -> Dict[str, Any]:
        """获取单机模式配置"""
        return {
            'QUEUE_TYPE': 'memory',
            'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
            'CONCURRENCY': 8,
            'MAX_RUNNING_SPIDERS': 1,
            'DOWNLOAD_DELAY': 1.0,
            'LOG_LEVEL': 'INFO',
        }
    
    @staticmethod
    def get_distributed_settings(
        redis_host: str = '127.0.0.1',
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0,  # 添加 redis_db 参数
        project_name: str = 'crawlo'
    ) -> Dict[str, Any]:
        """获取分布式模式配置"""
        # 构建 Redis URL，使用传入的 redis_db 参数
        if redis_password:
            redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
        else:
            redis_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
        
        return {
            'PROJECT_NAME': project_name,  # 添加项目名称到配置中
            'QUEUE_TYPE': 'redis',
            'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
            'REDIS_HOST': redis_host,
            'REDIS_PORT': redis_port,
            'REDIS_PASSWORD': redis_password,
            'REDIS_DB': redis_db,  # 添加 Redis 数据库编号到配置中
            'REDIS_URL': redis_url,
            'SCHEDULER_QUEUE_NAME': f'crawlo:{project_name}:queue:requests',  # 使用统一命名规范
            # Redis key配置已移至各组件中，使用统一的命名规范
            # crawlo:{project_name}:filter:fingerprint (请求去重)
            'CONCURRENCY': 16,
            'MAX_RUNNING_SPIDERS': 1,
            'DOWNLOAD_DELAY': 1.0,
            'LOG_LEVEL': 'INFO',
        }
    
    @staticmethod
    def get_auto_settings() -> Dict[str, Any]:
        """获取自动检测模式配置"""
        return {
            'QUEUE_TYPE': 'auto',
            'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',  # 默认内存过滤器
            'CONCURRENCY': 12,
            'MAX_RUNNING_SPIDERS': 1,
            'DOWNLOAD_DELAY': 1.0,
            'LOG_LEVEL': 'INFO',
        }
    
    def resolve_mode_settings(
        self, 
        mode: str = 'standalone',
        **kwargs
    ) -> Dict[str, Any]:
        """
        解析运行模式并返回对应配置
        
        Args:
            mode: 运行模式 ('standalone', 'distributed', 'auto')
            **kwargs: 额外配置参数
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        mode = RunMode(mode.lower())
        
        if mode == RunMode.STANDALONE:
            self.logger.info("使用单机模式 - 简单快速，适合开发和中小规模爬取")
            settings = self.get_standalone_settings()
            
        elif mode == RunMode.DISTRIBUTED:
            self.logger.info("使用分布式模式 - 支持多节点扩展，适合大规模爬取")
            settings = self.get_distributed_settings(
                redis_host=kwargs.get('redis_host', '127.0.0.1'),
                redis_port=kwargs.get('redis_port', 6379),
                redis_password=kwargs.get('redis_password'),
                redis_db=kwargs.get('redis_db', 0),  # 添加 redis_db 参数
                project_name=kwargs.get('project_name', 'crawlo')
            )
            
        elif mode == RunMode.AUTO:
            self.logger.info("使用自动检测模式 - 智能选择最佳运行方式")
            settings = self.get_auto_settings()
            
        else:
            raise ValueError(f"不支持的运行模式: {mode}")
        
        # 合并用户自定义配置
        user_settings = {k: v for k, v in kwargs.items() 
                        if k not in ['redis_host', 'redis_port', 'redis_password', 'project_name']}
        settings.update(user_settings)
        
        return settings
    
    def from_environment(self) -> Dict[str, Any]:
        """从环境变量构建配置"""
        config = {}
        
        # 扫描 CRAWLO_ 前缀的环境变量
        for key, value in os.environ.items():
            if key.startswith('CRAWLO_'):
                config_key = key[7:]  # 去掉 'CRAWLO_' 前缀
                # 简单的类型转换
                if value.lower() in ('true', 'false'):
                    config[config_key] = value.lower() == 'true'
                elif value.isdigit():
                    config[config_key] = int(value)
                else:
                    try:
                        config[config_key] = float(value)
                    except ValueError:
                        config[config_key] = value
        
        return config


# 便利函数
def standalone_mode(**kwargs) -> Dict[str, Any]:
    """快速创建单机模式配置"""
    return ModeManager().resolve_mode_settings('standalone', **kwargs)


def distributed_mode(
    redis_host: str = '127.0.0.1',
    redis_port: int = 6379,
    redis_password: Optional[str] = None,
    redis_db: int = 0,  # 添加 redis_db 参数
    project_name: str = 'crawlo',
    **kwargs
) -> Dict[str, Any]:
    """快速创建分布式模式配置"""
    return ModeManager().resolve_mode_settings(
        'distributed',
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        redis_db=redis_db,  # 传递 redis_db 参数
        project_name=project_name,
        **kwargs
    )


def auto_mode(**kwargs) -> Dict[str, Any]:
    """快速创建自动检测模式配置"""
    return ModeManager().resolve_mode_settings('auto', **kwargs)


# 环境变量支持
def from_env(default_mode: str = 'standalone') -> Dict[str, Any]:
    """从环境变量创建配置"""
    # 移除直接使用 os.getenv()，要求通过 settings 配置
    raise RuntimeError("环境变量配置已移除，请在 settings 中配置相关参数")
    
    # 保留原有代码作为参考
    # mode = os.getenv('CRAWLO_MODE', default_mode).lower()
    # 
    # if mode == 'distributed':
    #     return distributed_mode(
    #         redis_host=os.getenv('REDIS_HOST', '127.0.0.1'),
    #         redis_port=int(os.getenv('REDIS_PORT', 6379)),
    #         redis_password=os.getenv('REDIS_PASSWORD'),
    #         project_name=os.getenv('PROJECT_NAME', 'crawlo'),
    #         CONCURRENCY=int(os.getenv('CONCURRENCY', 16)),
    #     )
    # elif mode == 'auto':
    #     return auto_mode(
    #         CONCURRENCY=int(os.getenv('CONCURRENCY', 12)),
    #     )
    # else:  # standalone
    #     return standalone_mode(
    #         CONCURRENCY=int(os.getenv('CONCURRENCY', 8)),
    #     )