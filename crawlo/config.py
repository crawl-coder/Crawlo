#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 配置中心
===============
统一管理框架的所有配置、运行模式切换及合法性验证。

核心特性：
1. 链式调用：支持 .set().enable_debug() 等链式操作。
2. 模式切换：内置 standalone, distributed, auto 三种模式。
3. 自动验证：在设置或更新配置时自动执行合法性检查。
4. 环境变量：支持从 CRAWLO_ 前缀的环境变量加载配置。
"""
import os
import json
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pprint import pformat

from crawlo.logging import get_logger
from crawlo.utils.redis import RedisConfig


# ==================== 常量与枚举 ====================

class RunMode(Enum):
    """运行模式枚举"""
    STANDALONE = "standalone"
    DISTRIBUTED = "distributed"
    AUTO = "auto"


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


# ==================== 配置验证器 ====================

class ConfigValidator:
    """配置验证器核心类"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        self.errors = []
        self.warnings = []
        
        self._validate_basic(config)
        self._validate_network(config)
        self._validate_concurrency(config)
        self._validate_queue(config)
        self._validate_redis(config)
        self._validate_logging(config)
        
        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_basic(self, config: Dict[str, Any]):
        p_name = config.get('PROJECT_NAME', 'crawlo')
        if not isinstance(p_name, str) or not p_name.strip():
            self.errors.append("PROJECT_NAME 必须是非空字符串")

    def _validate_network(self, config: Dict[str, Any]):
        timeout = config.get('DOWNLOAD_TIMEOUT', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.errors.append("DOWNLOAD_TIMEOUT 必须是正数")
        
        delay = config.get('DOWNLOAD_DELAY', 1.0)
        if not isinstance(delay, (int, float)) or delay < 0:
            self.errors.append("DOWNLOAD_DELAY 必须是非负数")

    def _validate_concurrency(self, config: Dict[str, Any]):
        concurrency = config.get('CONCURRENCY', 8)
        if not isinstance(concurrency, int) or concurrency <= 0:
            self.errors.append("CONCURRENCY 必须是正整数")

    def _validate_queue(self, config: Dict[str, Any]):
        q_type = config.get('QUEUE_TYPE', 'memory')
        if q_type not in ['memory', 'redis', 'auto']:
            self.errors.append(f"QUEUE_TYPE 无效: {q_type}")

    def _validate_redis(self, config: Dict[str, Any]):
        if config.get('QUEUE_TYPE') == 'redis':
            host = config.get('REDIS_HOST', '127.0.0.1')
            if not isinstance(host, str) or not host.strip():
                self.errors.append("使用 Redis 模式时 REDIS_HOST 不能为空")

    def _validate_logging(self, config: Dict[str, Any]):
        level = config.get('LOG_LEVEL', 'INFO')
        if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            self.errors.append(f"LOG_LEVEL 无效: {level}")


# ==================== 配置中心核心类 ====================

class CrawloConfig:
    """
    Crawlo 配置工厂类
    
    统一管理配置的加载、切换和验证。
    """
    
    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings: Dict[str, Any] = settings
        self.logger = get_logger(self.__class__.__name__)
        self.validator = ConfigValidator()
        self._validate_settings()
    
    def _validate_settings(self, raise_error: bool = True) -> bool:
        """内部验证方法"""
        is_valid, errors, warnings = self.validator.validate(self.settings)
        
        if warnings:
            for w in warnings: self.logger.warning(f"配置警告: {w}")
            
        if not is_valid and raise_error:
            error_msg = "配置验证失败:\n" + "\n".join([f"  - {e}" for e in errors])
            raise ValueError(error_msg)
            
        return is_valid

    # ----- 链式操作接口 -----
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> 'CrawloConfig':
        self.settings[key] = value
        self._validate_settings()
        return self
    
    def update(self, settings: Dict[str, Any]) -> 'CrawloConfig':
        self.settings.update(settings)
        self._validate_settings()
        return self
    
    def enable_debug(self) -> 'CrawloConfig':
        return self.set('LOG_LEVEL', 'DEBUG')
    
    def set_concurrency(self, count: int) -> 'CrawloConfig':
        return self.set('CONCURRENCY', count)

    def to_dict(self) -> Dict[str, Any]:
        return self.settings.copy()

    # ----- 运行模式静态工厂 -----
    
    @classmethod
    def standalone(cls, **kwargs) -> 'CrawloConfig':
        """单机模式"""
        settings = BASE_CONFIG.copy()
        settings.update(MODE_CONFIG_MAP['standalone'])
        settings.update({k.upper(): v for k, v in kwargs.items()})
        return cls(settings)
    
    @classmethod
    def distributed(cls, redis_host='127.0.0.1', redis_port=6379, project_name='crawlo', **kwargs) -> 'CrawloConfig':
        """分布式模式"""
        redis_cfg = RedisConfig(host=redis_host, port=redis_port, **kwargs)
        settings = BASE_CONFIG.copy()
        settings.update(MODE_CONFIG_MAP['distributed'])
        settings.update({
            'REDIS_HOST': redis_host,
            'REDIS_PORT': redis_port,
            'REDIS_URL': redis_cfg.to_url(),
            'PROJECT_NAME': project_name,
            'SCHEDULER_QUEUE_NAME': f'crawlo:{project_name}:queue:requests',
        })
        # 合并剩余参数（转换为大写以匹配配置规范）
        settings.update({k.upper(): v for k, v in kwargs.items()})
        return cls(settings)
    
    @classmethod
    def auto(cls, project_name='crawlo', **kwargs) -> 'CrawloConfig':
        """自动检测模式"""
        settings = BASE_CONFIG.copy()
        settings.update(MODE_CONFIG_MAP['standalone'])
        settings.update({
            'RUN_MODE': 'auto',
            'QUEUE_TYPE': 'auto',
            'PROJECT_NAME': project_name
        })
        settings.update({k.upper(): v for k, v in kwargs.items()})
        return cls(settings)

    @classmethod
    def from_env(cls, default_mode: str = 'standalone') -> 'CrawloConfig':
        """从环境变量加载配置"""
        mode = os.getenv('CRAWLO_MODE', default_mode).lower()
        
        # 基础参数映射
        env_map = {
            'CRAWLO_REDIS_HOST': 'redis_host',
            'CRAWLO_REDIS_PORT': 'redis_port',
            'CRAWLO_PROJECT_NAME': 'project_name',
        }
        
        kwargs = {}
        for env_key, param_name in env_map.items():
            val = os.getenv(env_key)
            if val: kwargs[param_name] = val
            
        if mode == 'distributed':
            return cls.distributed(**kwargs)
        elif mode == 'auto':
            return cls.auto(**kwargs)
        return cls.standalone(**kwargs)

    def print_summary(self):
        """打印美化的配置报告"""
        print("\n" + "="*20 + " Crawlo Config Summary " + "="*20)
        print(f"Project: {self.get('PROJECT_NAME')}")
        print(f"Run Mode: {self.get('RUN_MODE')}")
        print(f"Concurrency: {self.get('CONCURRENCY')}")
        if self.get('REDIS_HOST'):
            print(f"Redis: {self.get('REDIS_HOST')}:{self.get('REDIS_PORT')}")
        print("="*63 + "\n")
        return self


# ==================== 便利函数 (保持向后兼容) ====================

def create_config(mode: str = 'standalone', **kwargs) -> CrawloConfig:
    if mode.lower() == 'standalone': return CrawloConfig.standalone(**kwargs)
    if mode.lower() == 'distributed': return CrawloConfig.distributed(**kwargs)
    if mode.lower() == 'auto': return CrawloConfig.auto(**kwargs)
    raise ValueError(f"Unknown mode: {mode}")

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    return ConfigValidator().validate(config)
