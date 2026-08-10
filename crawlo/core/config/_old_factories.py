#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CrawloConfig 静态工厂
=====================
standalone / distributed / auto / from_env 工厂方法的实现。
"""
import os
from typing import TYPE_CHECKING, Dict, Any, Optional, List, Type

if TYPE_CHECKING:
    from crawlo.core.config import CrawloConfig

from crawlo.core.config_base import BASE_CONFIG, MODE_CONFIG_MAP


# ==================== 工厂实现 ====================

def _make_standalone(cls: Type['CrawloConfig'],
                     project_name: str = 'crawlo',
                     **kwargs) -> 'CrawloConfig':
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
    from crawlo.utils.redis import RedisConfig  # 延迟：避免 lint-imports 计为 config_factories → utils.redis 顶层违规
    redis_host = kwargs.pop('REDIS_HOST', '127.0.0.1')
    redis_port = kwargs.pop('REDIS_PORT', 6379)
    redis_password = kwargs.pop('REDIS_PASSWORD', '')
    redis_username = kwargs.pop('REDIS_USER', '')
    redis_db = kwargs.pop('REDIS_DB', 0)

    # 兼容旧参数名（redis_host 等小写形式）
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
        host=redis_host,
        port=redis_port,
        password=redis_password,
        username=redis_username,
        db=redis_db,
    )

    # Sentinel 配置
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
    """Auto 模式：Redis 可用时自动切 Redis 去重 + ZSET 队列"""
    settings = BASE_CONFIG.copy()
    settings.update(MODE_CONFIG_MAP['standalone'])
    settings.update({
        'RUN_MODE': 'auto',
        'QUEUE_TYPE': 'auto',
        'PROJECT_NAME': project_name
    })
    settings.update({k.upper(): v for k, v in kwargs.items()})

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


__all__ = [
    '_make_standalone',
    '_make_distributed',
    '_make_auto',
    '_make_from_env',
]
