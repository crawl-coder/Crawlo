#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 配置中心
================
面向用户的配置入口，提供链式 API、模式切换、环境变量加载。

核心 API：
    from crawlo.core.config import CrawloConfig
    config = CrawloConfig.auto(project_name='demo', concurrency=12)
    config = CrawloConfig.standalone().set('LOG_LEVEL', 'DEBUG').enable_debug()
    config = CrawloConfig.from_env()
    locals().update(config.to_dict())
"""
import os
from typing import Dict, Any, Optional, List, Tuple, Type

from crawlo.logging import get_logger

# ==================== 工厂实现（原 crawlo.core.config_factories） ====================

def _make_standalone(cls: Type['CrawloConfig'],
                     project_name: str = 'crawlo',
                     **kwargs) -> 'CrawloConfig':
    from crawlo.core.config.base import BASE_CONFIG, MODE_CONFIG_MAP
    settings = BASE_CONFIG.copy()
    settings.update(MODE_CONFIG_MAP['standalone'])
    settings['PROJECT_NAME'] = project_name
    settings.update({k.upper(): v for k, v in kwargs.items()})
    return cls(settings)


def _make_distributed(cls: Type['CrawloConfig'],
                      project_name: str = 'crawlo',
                      sentinel_urls: Optional[List[str]] = None,
                      sentinel_service: str = 'mymaster',
                      **kwargs) -> 'CrawloConfig':
    from crawlo.utils.redis import RedisConfig
    from crawlo.core.config.base import BASE_CONFIG, MODE_CONFIG_MAP
    redis_host = kwargs.pop('REDIS_HOST', '127.0.0.1')
    redis_port = kwargs.pop('REDIS_PORT', 6379)
    redis_password = kwargs.pop('REDIS_PASSWORD', '')
    redis_username = kwargs.pop('REDIS_USER', '')
    redis_db = kwargs.pop('REDIS_DB', 0)
    redis_host = kwargs.pop('redis_host', redis_host)
    redis_port = kwargs.pop('redis_port', redis_port)
    redis_password = kwargs.pop('redis_password', redis_password)
    redis_username = kwargs.pop('redis_username', redis_username)
    redis_db = kwargs.pop('redis_db', redis_db)
    if redis_password == '':  # nosec B105
        redis_password = None
    if redis_username == '':
        redis_username = None
    redis_cfg = RedisConfig(
        host=redis_host, port=redis_port,
        password=redis_password, username=redis_username, db=redis_db,
    )
    effective_sentinel_urls = list(sentinel_urls or [])
    sentinel_urls_kwargs = kwargs.pop('sentinel_urls', None)
    if sentinel_urls_kwargs:
        effective_sentinel_urls = list(sentinel_urls_kwargs)
    sentinel_service_val = sentinel_service
    sentinel_service_kwargs = kwargs.pop('sentinel_service', None)
    if sentinel_service_kwargs:
        sentinel_service_val = sentinel_service_kwargs
    settings = BASE_CONFIG.copy()
    settings.update(MODE_CONFIG_MAP['distributed'])
    settings.update({
        'REDIS_HOST': redis_host,
        'REDIS_PORT': redis_port,
        'REDIS_PASSWORD': redis_password,
        'REDIS_USER': redis_username,
        'REDIS_DB': redis_db,
        'REDIS_URL': redis_cfg.to_url(),
        'REDIS_SENTINEL_URLS': effective_sentinel_urls,
        'REDIS_SENTINEL_SERVICE': sentinel_service_val,
        'PROJECT_NAME': project_name,
        'SCHEDULER_QUEUE_NAME': f'crawlo:{project_name}:queue:requests',
    })
    settings.update({k.upper(): v for k, v in kwargs.items()})
    return cls(settings)


def _make_auto(cls: Type['CrawloConfig'],
               project_name: str = 'crawlo',
               **kwargs) -> 'CrawloConfig':
    """Auto 模式配置工厂：
    - Redis 可用：用 Redis ZSET 队列 + Redis 去重（AioRedisFilter + RedisDedupPipeline）
    - Redis 不可用：fallback 到 Memory 队列 + Memory 去重
    """
    from crawlo.core.config.base import BASE_CONFIG, MODE_CONFIG_MAP
    settings = BASE_CONFIG.copy()
    settings.update(MODE_CONFIG_MAP['standalone'])
    settings.update({
        'RUN_MODE': 'auto',
        'QUEUE_TYPE': 'auto',
        'PROJECT_NAME': project_name,
    })
    settings.update({k.upper(): v for k, v in kwargs.items()})

    # Redis 可用性探测 → 决定去重组件（队列在 QueueManager._determine_queue_type 中动态切换）
    redis_host = settings.get('REDIS_HOST') or '127.0.0.1'
    redis_port = settings.get('REDIS_PORT') or 6379
    redis_password = settings.get('REDIS_PASSWORD') or None
    redis_db = settings.get('REDIS_DB') or 0
    try:
        import redis as _sync_redis
        _r = _sync_redis.Redis(
            host=redis_host, port=int(redis_port),
            password=redis_password, db=int(redis_db),
            socket_connect_timeout=1.5, socket_timeout=1.5,
        )
        _ok = _r.ping()
        _r.close()
    except Exception:
        _ok = False

    if _ok:
        settings.update({
            'FILTER_CLASS': 'crawlo.filters.AioRedisFilter',
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.RedisDedupPipeline',
        })
        from crawlo.utils.redis import RedisConfig
        redis_cfg = RedisConfig(
            host=redis_host, port=int(redis_port),
            password=redis_password, db=int(redis_db),
        )
        settings.setdefault('REDIS_URL', redis_cfg.to_url())
    return cls(settings)


def _make_from_env(cls: Type['CrawloConfig'],
                   default_mode: str = 'standalone') -> 'CrawloConfig':
    env_map = {
        'CRAWLO_MODE': ('mode', str, default_mode),
        'CRAWLO_REDIS_HOST': ('redis_host', str, '127.0.0.1'),
        'CRAWLO_REDIS_PORT': ('redis_port', int, 6379),
        'CRAWLO_REDIS_PASSWORD': ('redis_password', str, None),
        'CRAWLO_REDIS_DB': ('redis_db', int, 0),
        'CRAWLO_PROJECT_NAME': ('project_name', str, 'crawlo'),
        'CRAWLO_CONCURRENCY': ('concurrency', int, None),
        'CRAWLO_LOG_LEVEL': ('log_level', str, None),
    }
    kwargs: Dict[str, Any] = {}
    mode = os.getenv('CRAWLO_MODE', default_mode).lower()
    for env_key, (config_key, type_converter, default_value) in env_map.items():
        value = os.getenv(env_key)
        if value is not None:
            if type_converter == int:
                kwargs[config_key] = int(value)
            elif type_converter == bool:
                kwargs[config_key] = value.lower() in ('true', '1', 'yes')
            elif type_converter == str:
                kwargs[config_key] = value
        elif default_value is not None:
            kwargs[config_key] = default_value
    if mode == 'distributed':
        return _make_distributed(cls, **kwargs)
    if mode == 'auto':
        return _make_auto(cls, **kwargs)
    return _make_standalone(cls, **kwargs)


class CrawloConfig:
    """
    Crawlo 配置工厂类

    统一管理配置的加载、切换、验证和导出。
    支持链式调用和三种运行模式。
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        """
        初始化配置

        Args:
            settings: 配置字典
        """
        from crawlo.core.config.validator import ConfigValidator
        self.settings: Dict[str, Any] = settings
        self.logger = get_logger(self.__class__.__name__)
        self.validator = ConfigValidator()
        self._validate_settings()

    def _validate_settings(self, raise_error: bool = True) -> bool:
        """内部验证方法"""
        is_valid, errors, warnings = self.validator.validate(self.settings)

        if warnings:
            for w in warnings:
                self.logger.warning(f"配置警告: {w}")

        if not is_valid and raise_error:
            error_msg = "配置验证失败:\n" + "\n".join([f"  - {e}" for e in errors])
            raise ValueError(error_msg)

        return is_valid

    # ----- 链式操作接口 -----

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> 'CrawloConfig':
        """
        设置配置项（链式操作）

        Args:
            key: 配置键
            value: 配置值

        Returns:
            self，支持链式调用
        """
        self.settings[key] = value
        self._validate_settings()
        return self

    def update(self, settings: Dict[str, Any]) -> 'CrawloConfig':
        """
        批量更新配置（链式操作）

        Args:
            settings: 配置字典

        Returns:
            self，支持链式调用
        """
        self.settings.update(settings)
        self._validate_settings()
        return self

    def enable_debug(self) -> 'CrawloConfig':
        """启用调试模式（链式操作）"""
        return self.set('LOG_LEVEL', 'DEBUG')

    def set_concurrency(self, count: int) -> 'CrawloConfig':
        """设置并发数（链式操作）"""
        return self.set('CONCURRENCY', count)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return self.settings.copy()

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """验证当前配置"""
        return self.validator.validate(self.settings)

    # ----- 运行模式静态工厂 -----

    @classmethod
    def standalone(cls, project_name: str = 'crawlo', **kwargs) -> 'CrawloConfig':
        """单机模式（内存队列，无需外部依赖）"""
        return _make_standalone(cls, project_name, **kwargs)

    @classmethod
    def distributed(cls,
                    project_name: str = 'crawlo',
                    sentinel_urls: Optional[List[str]] = None,
                    sentinel_service: str = 'mymaster',
                    **kwargs) -> 'CrawloConfig':
        """分布式模式（Redis 队列，多节点扩展）"""
        return _make_distributed(cls, project_name, sentinel_urls, sentinel_service, **kwargs)

    @classmethod
    def auto(cls, project_name: str = 'crawlo', **kwargs) -> 'CrawloConfig':
        """自动检测模式（推荐）：运行时探测 Redis 可用性"""
        return _make_auto(cls, project_name, **kwargs)

    @classmethod
    def from_env(cls, default_mode: str = 'standalone') -> 'CrawloConfig':
        """从环境变量加载配置（CRAWLO_* 前缀）"""
        return _make_from_env(cls, default_mode)

    def print_summary(self) -> 'CrawloConfig':
        """打印配置摘要（链式操作）"""
        print("\n" + "=" * 20 + " Crawlo Config Summary " + "=" * 20)
        print(f"Project: {self.get('PROJECT_NAME')}")
        print(f"Run Mode: {self.get('RUN_MODE')}")
        print(f"Concurrency: {self.get('CONCURRENCY')}")
        if self.get('REDIS_HOST'):
            print(f"Redis: {self.get('REDIS_HOST')}:{self.get('REDIS_PORT')}")
        print("=" * 63 + "\n")
        return self


__all__ = ['CrawloConfig']
