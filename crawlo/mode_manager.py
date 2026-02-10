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

from crawlo.utils.redis_config import RedisConfig


# 常量定义
BASE_CONFIG = {
    'PROJECT_NAME': 'crawlo',
    'CONCURRENCY': 8,
    'MAX_RUNNING_SPIDERS': 1,
    'DOWNLOAD_DELAY': 1.0,
}

MODE_CONFIG_MAP = {
    'standalone': {
        'RUN_MODE': 'standalone',
        'QUEUE_TYPE': 'memory',
        'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
    },
    'distributed': {
        'RUN_MODE': 'distributed',
        'QUEUE_TYPE': 'redis',
        'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
    }
}

# 辅助函数：环境变量值类型转换
def _convert_env_value(value: str):
    """环境变量值类型转换辅助函数"""
    # 布尔值转换
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    # 整数转换
    if value.isdigit():
        return int(value)
    # 浮点数转换
    try:
        return float(value)
    except ValueError:
        # 字符串值
        return value


class RunMode(Enum):
    """运行模式枚举"""
    STANDALONE = "standalone"  # 单机模式
    DISTRIBUTED = "distributed"  # 分布式模式
    AUTO = "auto"  # 自动检测模式


class ModeManager:
    """运行模式管理器"""

    def __init__(self):
        # 延迟初始化logger，避免循环依赖
        self._logger = None
        self._debug("运行模式管理器初始化完成")

    def _get_logger(self):
        """延迟获取logger实例"""
        if self._logger is None:
            try:
                from crawlo.logging import get_logger
                self._logger = get_logger(__name__)
            except Exception:
                # 如果日志系统尚未初始化，返回None
                pass
        return self._logger

    def _debug(self, message: str):
        """调试日志"""
        logger = self._get_logger()
        if logger:
            logger.debug(message)

    @staticmethod
    def get_standalone_settings() -> Dict[str, Any]:
        """获取单机模式配置"""
        config = BASE_CONFIG.copy()
        config.update(MODE_CONFIG_MAP['standalone'])
        return config

    @staticmethod
    def get_distributed_settings(
            redis_host: str = '127.0.0.1',
            redis_port: int = 6379,
            redis_password: Optional[str] = None,
            redis_username: Optional[str] = None,
            redis_db: int = 0,
            redis_ssl: bool = False,
            project_name: str = 'crawlo',
            **redis_kwargs
    ) -> Dict[str, Any]:
        """获取分布式模式配置"""
        # 使用新的 Redis 配置类
        redis_config = RedisConfig(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            username=redis_username,
            db=redis_db,
            ssl=redis_ssl,
            **redis_kwargs
        )
        
        # 生成 Redis URL
        redis_url = redis_config.to_url()
        
        config = BASE_CONFIG.copy()
        config.update(MODE_CONFIG_MAP['distributed'])
        config.update({
            'REDIS_HOST': redis_host,
            'REDIS_PORT': redis_port,
            'REDIS_PASSWORD': redis_password,
            'REDIS_USERNAME': redis_username,
            'REDIS_DB': redis_db,
            'REDIS_SSL': redis_ssl,
            'REDIS_URL': redis_url,
            'SCHEDULER_QUEUE_NAME': f'crawlo:{project_name}:queue:requests',
            'PROJECT_NAME': project_name,
            'CONCURRENCY': 16,
            'MAX_RUNNING_SPIDERS': 10,
        })
        
        # 添加额外的 Redis 参数
        config.update(redis_kwargs)
        return config

    @staticmethod
    def get_auto_settings(project_name: str = 'crawlo') -> Dict[str, Any]:
        """获取自动检测模式配置"""
        # 默认使用内存队列和过滤器
        settings = ModeManager.get_standalone_settings()
        settings['RUN_MODE'] = 'auto'
        settings['QUEUE_TYPE'] = 'auto'
        # 使用传入的项目名称而不是硬编码的'crawlo'
        settings['PROJECT_NAME'] = project_name
        return settings

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
        self._debug(f"解析运行模式: {mode}")
        mode_enum = RunMode(mode.lower())
        
        # 使用字典映射替代 if-elif 判断
        mode_handlers = {
            RunMode.STANDALONE: (self._get_standalone_settings_with_args, 
                               "使用单机模式 - 简单快速，适合开发和中小规模爬取"),
            RunMode.DISTRIBUTED: (self._get_distributed_settings_with_args, 
                                "使用分布式模式 - 支持多节点扩展，适合大规模爬取"),
            RunMode.AUTO: (self._get_auto_settings_with_args, 
                         "使用自动检测模式 - 智能选择最佳运行方式")
        }
        
        if mode_enum not in mode_handlers:
            raise ValueError(f"不支持的运行模式: {mode}")
            
        handler, mode_info = mode_handlers[mode_enum]
        settings = handler(**kwargs)
        self._debug(f"应用{mode}模式配置")
        
        # 合并用户自定义配置（使用已优化的逻辑）
        settings = self._merge_user_settings(settings, mode_enum, **kwargs)
        self._debug(f"合并用户自定义配置: {list(settings.keys())}")
        
        # 将模式信息添加到配置中
        settings['_mode_info'] = mode_info
        self._debug(f"运行模式解析完成: {mode}")
        return settings

    def _get_standalone_settings_with_args(self, **kwargs):
        """带参数的单机配置获取"""
        return self.get_standalone_settings()
    
    def _get_distributed_settings_with_args(self, **kwargs):
        """带参数的分布式配置获取"""
        return self.get_distributed_settings(
            redis_host=kwargs.get('redis_host', '127.0.0.1'),
            redis_port=kwargs.get('redis_port', 6379),
            redis_password=kwargs.get('redis_password'),
            redis_db=kwargs.get('redis_db', 0),
            project_name=kwargs.get('project_name', 'crawlo')
        )
    
    def _get_auto_settings_with_args(self, **kwargs):
        """带参数的自动模式配置获取"""
        return self.get_auto_settings(project_name=kwargs.get('project_name', 'crawlo'))
    
    def _merge_user_settings(self, settings: Dict[str, Any], mode_enum: RunMode, **kwargs) -> Dict[str, Any]:
        """合并用户自定义配置的通用方法"""
        redis_params = ['redis_host', 'redis_port', 'redis_password']
        distributed_only_params = redis_params + ['project_name']
        
        if mode_enum == RunMode.DISTRIBUTED:
            user_settings = {
                k.upper(): v for k, v in kwargs.items() 
                if k not in distributed_only_params
            }
            if 'project_name' in kwargs:
                settings['PROJECT_NAME'] = kwargs['project_name']
        else:
            user_settings = {
                k.upper(): v for k, v in kwargs.items() 
                if k not in redis_params
            }
            if 'project_name' in kwargs:
                settings['PROJECT_NAME'] = kwargs['project_name']
                
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
                config[config_key] = _convert_env_value(value)

        return config


# 便利函数
def standalone_mode(
        project_name: str = 'crawlo',
        **kwargs
) -> Dict[str, Any]:
    """快速创建单机模式配置"""
    return ModeManager().resolve_mode_settings(
        'standalone',
        project_name=project_name,
        **kwargs
    )


def distributed_mode(
        redis_host: str = '127.0.0.1',
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_username: Optional[str] = None,
        redis_db: int = 0,
        redis_ssl: bool = False,
        project_name: str = 'crawlo',
        **kwargs
) -> Dict[str, Any]:
    """快速创建分布式模式配置"""
    return ModeManager().resolve_mode_settings(
        'distributed',
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        redis_username=redis_username,
        redis_db=redis_db,
        redis_ssl=redis_ssl,
        project_name=project_name,
        **kwargs
    )


def auto_mode(
        project_name: str = 'crawlo',
        **kwargs
) -> Dict[str, Any]:
    """快速创建自动检测模式配置"""
    return ModeManager().resolve_mode_settings(
        'auto',
        project_name=project_name,
        **kwargs
    )


# 环境变量支持
def from_env(default_mode: str = 'standalone') -> Dict[str, Any]:
    """从环境变量创建配置
    
    支持的环境变量：
    - CRAWLO_MODE: 运行模式 (standalone/distributed/auto)
    - CRAWLO_REDIS_HOST: Redis主机地址
    - CRAWLO_REDIS_PORT: Redis端口
    - CRAWLO_REDIS_PASSWORD: Redis密码
    - CRAWLO_REDIS_USERNAME: Redis用户名
    - CRAWLO_REDIS_DB: Redis数据库编号
    - CRAWLO_REDIS_SSL: 是否使用SSL连接
    - CRAWLO_PROJECT_NAME: 项目名称
    - CRAWLO_CONCURRENCY: 并发数
    
    Args:
        default_mode: 默认运行模式（当未设置环境变量时使用）
    
    Returns:
        配置字典
    """
    # 环境变量配置映射
    env_config_map = {
        'CRAWLO_MODE': ('mode', str, default_mode),
        'CRAWLO_REDIS_HOST': ('redis_host', str, '127.0.0.1'),
        'CRAWLO_REDIS_PORT': ('redis_port', int, 6379),
        'CRAWLO_REDIS_PASSWORD': ('redis_password', str, None),
        'CRAWLO_REDIS_USERNAME': ('redis_username', str, None),
        'CRAWLO_REDIS_DB': ('redis_db', int, 0),
        'CRAWLO_REDIS_SSL': ('redis_ssl', bool, False),
        'CRAWLO_PROJECT_NAME': ('project_name', str, None),
        'CRAWLO_CONCURRENCY': ('CONCURRENCY', int, None),
    }
    
    kwargs = {}
    mode = os.getenv('CRAWLO_MODE', default_mode).lower()
    
    # 统一处理环境变量
    for env_key, (config_key, type_converter, default_value) in env_config_map.items():
        value = os.getenv(env_key)
        if value is not None:
            if type_converter == int:
                kwargs[config_key] = int(value)
            elif type_converter == bool:
                kwargs[config_key] = value.lower() in ('true', '1', 'yes')
            elif type_converter == str:
                kwargs[config_key] = value
        elif default_value is not None and config_key not in kwargs:
            kwargs[config_key] = default_value
    
    return ModeManager().resolve_mode_settings(mode, **kwargs)
