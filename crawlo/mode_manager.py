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


class RunMode(Enum):
    """运行模式枚举"""
    STANDALONE = "standalone"  # 单机模式
    DISTRIBUTED = "distributed"  # 分布式模式
    AUTO = "auto"  # 自动检测模式


def generate_redis_url(host: str, port: int, password: Optional[str], db: int) -> str:
    """
    根据Redis连接参数生成Redis URL
    
    Args:
        host: Redis主机地址
        port: Redis端口
        password: Redis密码（可选）
        db: Redis数据库编号
        
    Returns:
        str: Redis URL
    """
    if password:
        return f'redis://:{password}@{host}:{port}/{db}'
    else:
        return f'redis://{host}:{port}/{db}'


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
        return {
            'RUN_MODE': 'standalone',
            'QUEUE_TYPE': 'memory',
            'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
            'PROJECT_NAME': 'crawlo',
            'CONCURRENCY': 8,
            'MAX_RUNNING_SPIDERS': 1,
            'DOWNLOAD_DELAY': 1.0,
        }

    @staticmethod
    def get_distributed_settings(
            redis_host: str = '127.0.0.1',
            redis_port: int = 6379,
            redis_password: Optional[str] = None,
            redis_db: int = 0,
            project_name: str = 'crawlo'
    ) -> Dict[str, Any]:
        """获取分布式模式配置"""
        # 构建 Redis URL
        redis_url = generate_redis_url(redis_host, redis_port, redis_password, redis_db)

        return {
            'RUN_MODE': 'distributed',
            'QUEUE_TYPE': 'redis',
            'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
            'REDIS_HOST': redis_host,
            'REDIS_PORT': redis_port,
            'REDIS_PASSWORD': redis_password,
            'REDIS_DB': redis_db,
            'REDIS_URL': redis_url,
            'PROJECT_NAME': project_name,
            'SCHEDULER_QUEUE_NAME': f'crawlo:{project_name}:queue:requests',
            'CONCURRENCY': 16,
            'MAX_RUNNING_SPIDERS': 10,
            'DOWNLOAD_DELAY': 1.0,
        }

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
        mode_info = None

        if mode_enum == RunMode.STANDALONE:
            mode_info = "使用单机模式 - 简单快速，适合开发和中小规模爬取"
            # 对于单机模式，如果用户设置了QUEUE_TYPE为'auto'，应该保留用户的设置
            settings = self.get_standalone_settings()
            self._debug("应用单机模式配置")

        elif mode_enum == RunMode.DISTRIBUTED:
            mode_info = "使用分布式模式 - 支持多节点扩展，适合大规模爬取"
            settings = self.get_distributed_settings(
                redis_host=kwargs.get('redis_host', '127.0.0.1'),
                redis_port=kwargs.get('redis_port', 6379),
                redis_password=kwargs.get('redis_password'),
                redis_db=kwargs.get('redis_db', 0),  # 添加 redis_db 参数
                project_name=kwargs.get('project_name', 'crawlo')
            )
            self._debug("应用分布式模式配置")

        elif mode_enum == RunMode.AUTO:
            mode_info = "使用自动检测模式 - 智能选择最佳运行方式"
            # 传递项目名称给get_auto_settings
            settings = self.get_auto_settings(
                project_name=kwargs.get('project_name', 'crawlo')
            )
            self._debug("应用自动检测模式配置")

        else:
            raise ValueError(f"不支持的运行模式: {mode}")

        # 合并用户自定义配置
        # 对于分布式模式，过滤掉特定参数
        if mode_enum == RunMode.DISTRIBUTED:
            user_settings = {
                k.upper(): v for k,
                v in kwargs.items() if k not in [
                    'redis_host',
                    'redis_port',
                    'redis_password',
                    'project_name']}
            # 特别处理project_name
            if 'project_name' in kwargs:
                settings['PROJECT_NAME'] = kwargs['project_name']
        else:
            # 对于单机模式和自动模式，只过滤Redis相关参数
            user_settings = {
                k.upper(): v for k,
                v in kwargs.items() if k not in [
                    'redis_host',
                    'redis_port',
                    'redis_password']}
            # 特别处理project_name
            if 'project_name' in kwargs:
                settings['PROJECT_NAME'] = kwargs['project_name']
        settings.update(user_settings)
        self._debug(f"合并用户自定义配置: {list(user_settings.keys())}")

        # 将模式信息添加到配置中，供后续使用
        settings['_mode_info'] = mode_info

        self._debug(f"运行模式解析完成: {mode}")
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
    - CRAWLO_REDIS_DB: Redis数据库编号
    - CRAWLO_PROJECT_NAME: 项目名称
    - CRAWLO_CONCURRENCY: 并发数
    
    Args:
        default_mode: 默认运行模式（当未设置环境变量时使用）
    
    Returns:
        配置字典
    """
    mode = os.getenv('CRAWLO_MODE', default_mode).lower()
    
    kwargs = {}
    
    # 分布式模式特有配置
    if mode == 'distributed':
        kwargs['redis_host'] = os.getenv('CRAWLO_REDIS_HOST', '127.0.0.1')
        kwargs['redis_port'] = int(os.getenv('CRAWLO_REDIS_PORT', '6379'))
        if password := os.getenv('CRAWLO_REDIS_PASSWORD'):
            kwargs['redis_password'] = password
        kwargs['redis_db'] = int(os.getenv('CRAWLO_REDIS_DB', '0'))
    
    # 通用配置
    if project_name := os.getenv('CRAWLO_PROJECT_NAME'):
        kwargs['project_name'] = project_name
    
    if concurrency := os.getenv('CRAWLO_CONCURRENCY'):
        kwargs['CONCURRENCY'] = int(concurrency)
    
    return ModeManager().resolve_mode_settings(mode, **kwargs)