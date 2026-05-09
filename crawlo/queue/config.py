#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
队列配置

封装队列类型、Redis 连接、背压策略等配置，
支持从 settings 自动构建。
"""
from typing import Optional, Union

from crawlo.queue.queue_types import QueueType
from crawlo.utils.misc import safe_get_config


class QueueConfig:
    """Queue configuration class"""

    def __init__(
            self,
            queue_type: Union[QueueType, str] = QueueType.AUTO,
            redis_url: Optional[str] = None,
            redis_host: str = "127.0.0.1",
            redis_port: int = 6379,
            redis_password: Optional[str] = None,
            redis_user: Optional[str] = None,
            redis_db: int = 0,
            queue_name: str = "crawlo:requests",
            max_queue_size: int = 1000,
            max_retries: int = 3,
            timeout: int = 300,
            run_mode: Optional[str] = None,
            settings=None,
            serialization_format: str = 'pickle',
            backpressure_ratio: float = 0.8,
            backpressure_delay_base: float = 0.5,
            backpressure_delay_max: float = 5.0,
            **kwargs
    ):
        self.queue_type = QueueType(queue_type) if isinstance(queue_type, str) else queue_type
        self.run_mode = run_mode
        self.settings = settings
        self.serialization_format = serialization_format

        # Redis 配置
        if redis_url:
            self.redis_url = redis_url
        else:
            if redis_user and redis_password:
                self.redis_url = f"redis://{redis_user}:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            elif redis_password:
                self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        self.queue_name = queue_name
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.backpressure_ratio = backpressure_ratio
        self.backpressure_delay_base = backpressure_delay_base
        self.backpressure_delay_max = backpressure_delay_max
        self.extra_config = kwargs

    @classmethod
    def from_settings(cls, settings) -> 'QueueConfig':
        """Create configuration from settings"""
        project_name = safe_get_config(settings, 'PROJECT_NAME', 'default')
        default_queue_name = f"crawlo:{project_name}:queue:requests"
        
        queue_name = safe_get_config(settings, 'SCHEDULER_QUEUE_NAME', default_queue_name)
        queue_type = safe_get_config(settings, 'QUEUE_TYPE', QueueType.AUTO)
        redis_url = safe_get_config(settings, 'REDIS_URL')
        redis_host = safe_get_config(settings, 'REDIS_HOST', '127.0.0.1')
        redis_password = safe_get_config(settings, 'REDIS_PASSWORD')
        redis_user = safe_get_config(settings, 'REDIS_USER')
        run_mode = safe_get_config(settings, 'RUN_MODE')
        
        redis_port = safe_get_config(settings, 'REDIS_PORT', 6379, int)
        redis_db = safe_get_config(settings, 'REDIS_DB', 0, int)
        max_retries = safe_get_config(settings, 'QUEUE_MAX_RETRIES', 3, int)
        timeout = safe_get_config(settings, 'QUEUE_TIMEOUT', 300, int)
        serialization_format = safe_get_config(settings, 'SERIALIZATION_FORMAT', 'pickle')
        
        queue_type_str = queue_type.value if isinstance(queue_type, QueueType) else str(queue_type).lower()
        
        # 根据队列类型获取背压配置
        if queue_type_str == 'redis':
            backpressure_config = cls._get_backpressure_config(
                settings, 'REDIS',
                defaults={
                    'max_size': 50000,
                    'ratio': 0.6,
                    'delay_base': 0.5,
                    'delay_max': 5.0,
                    'warning_threshold': 0.5,
                    'critical_threshold': 0.8
                }
            )
        elif queue_type_str == 'memory':
            backpressure_config = cls._get_backpressure_config(
                settings, 'MEMORY',
                defaults={
                    'max_size': 5000,
                    'ratio': 0.8,
                    'delay_base': 0.2,
                    'delay_max': 2.0,
                    'warning_threshold': 0.7,
                    'critical_threshold': 0.9
                }
            )
        else:  # auto
            backpressure_config = cls._get_backpressure_config(
                settings, '',
                defaults={
                    'max_size': 10000,
                    'ratio': 0.75,
                    'delay_base': 0.2,
                    'delay_max': 3.0,
                    'warning_threshold': 0.7,
                    'critical_threshold': 0.9
                }
            )
        
        backpressure_check_interval = safe_get_config(settings, 'BACKPRESSURE_CHECK_INTERVAL', 0.1)
        
        return cls(
            queue_type=queue_type,
            redis_url=redis_url,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            redis_user=redis_user,
            redis_db=redis_db,
            queue_name=queue_name,
            max_queue_size=backpressure_config['max_queue_size'],
            max_retries=max_retries,
            timeout=timeout,
            run_mode=run_mode,
            settings=settings,
            serialization_format=serialization_format,
            backpressure_ratio=backpressure_config['backpressure_ratio'],
            backpressure_delay_base=backpressure_config['backpressure_delay_base'],
            backpressure_delay_max=backpressure_config['backpressure_delay_max'],
            extra_config={
                'backpressure_check_interval': backpressure_check_interval,
                'backpressure_warning_threshold': backpressure_config['backpressure_warning_threshold'],
                'backpressure_critical_threshold': backpressure_config['backpressure_critical_threshold'],
            }
        )
    
    @staticmethod
    def _get_backpressure_config(settings, prefix: str, defaults: dict) -> dict:
        """
        提取背压配置（带前缀fallback）
        
        Args:
            settings: 配置对象
            prefix: 配置前缀（如 'REDIS', 'MEMORY'）
            defaults: 默认值字典
            
        Returns:
            背压配置字典
        """
        # 构建带前缀的配置键
        def get_with_prefix(base_key, fallback_key=None):
            if prefix:
                return safe_get_config(
                    settings, f'{prefix}_{base_key}',
                    safe_get_config(settings, fallback_key or base_key, defaults.get(base_key.split('_')[-1].lower()))
                )
            else:
                return safe_get_config(settings, base_key, defaults.get(base_key.split('_')[-1].lower()))
        
        return {
            'max_queue_size': get_with_prefix('SCHEDULER_MAX_QUEUE_SIZE', 'SCHEDULER_MAX_QUEUE_SIZE') if prefix else safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', defaults['max_size'], int),
            'backpressure_ratio': get_with_prefix('BACKPRESSURE_RATIO'),
            'backpressure_delay_base': get_with_prefix('BACKPRESSURE_DELAY_BASE'),
            'backpressure_delay_max': get_with_prefix('BACKPRESSURE_DELAY_MAX'),
            'backpressure_warning_threshold': get_with_prefix('BACKPRESSURE_WARNING_THRESHOLD'),
            'backpressure_critical_threshold': get_with_prefix('BACKPRESSURE_CRITICAL_THRESHOLD'),
        }
