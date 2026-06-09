#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 配置中心
===============
统一管理框架的所有配置、运行模式切换及合法性验证。

与 settings/ 包的职责划分：
- config.py: 面向用户的配置入口，提供链式 API、模式切换、环境变量加载
- settings/: 框架内部各模块的默认参数定义，不应被用户直接导入

核心特性：
1. 链式调用：支持 .set().enable_debug() 等链式操作
2. 模式切换：内置 standalone, distributed, auto 三种模式
3. 自动验证：在设置或更新配置时自动执行合法性检查
4. 环境变量：支持从 CRAWLO_ 前缀的环境变量加载配置

使用示例：
    from crawlo.config import CrawloConfig
    
    # 方式1：工厂方法
    config = CrawloConfig.auto(project_name='myproject', concurrency=12)
    
    # 方式2：链式操作
    config = CrawloConfig.standalone().set('LOG_LEVEL', 'DEBUG').enable_debug()
    
    # 方式3：环境变量
    config = CrawloConfig.from_env()
    
    # 应用到 settings
    locals().update(config.to_dict())
"""
import os
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pprint import pformat

from crawlo.logging import get_logger
from crawlo.utils.redis import RedisConfig


# ==================== 常量与枚举 ====================

class RunMode(Enum):
    """运行模式枚举"""
    STANDALONE = "standalone"   # 单机模式
    DISTRIBUTED = "distributed" # 分布式模式
    AUTO = "auto"               # 自动检测模式


# 基础配置默认值
BASE_CONFIG = {
    'PROJECT_NAME': 'crawlo',
    'CONCURRENCY': 8,
    'MAX_RUNNING_SPIDERS': 1,
    'DOWNLOAD_DELAY': 1.0,
    'DOWNLOAD_TIMEOUT': 30,
    'MAX_RETRY_TIMES': 3,
    'CONNECTION_POOL_LIMIT': 50,
    'LOG_LEVEL': 'INFO',
}

# 运行模式配置映射
MODE_CONFIG_MAP = {
    'standalone': {
        'RUN_MODE': 'standalone',
        'QUEUE_TYPE': 'memory',
        'FILTER_CLASS': 'crawlo.filters.MemoryFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.MemoryDedupPipeline',
    },
    'distributed': {
        'RUN_MODE': 'distributed',
        'QUEUE_TYPE': 'redis_stream',
        'FILTER_CLASS': 'crawlo.filters.AioRedisFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.RedisDedupPipeline',
        'CONCURRENCY': 16,
        'MAX_RUNNING_SPIDERS': 10,
        'DISTRIBUTED_WORKER_IDLE_TIMEOUT': 300,   # 连续空闲 N 秒后退出（0 = 永不退出）
        'STREAM_DELIVERY_COUNT_LIMIT': 3,           # Stream 最大投递次数
        'STREAM_CONSUMER_IDLE_TIMEOUT': 60000,      # ms，任务超时未 ACK 可回收
    }
}


# ==================== 配置验证器 ====================

class ConfigValidator:
    """配置验证器 - 确保配置的合理性和一致性"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            Tuple[bool, List[str], List[str]]: (是否有效, 错误列表, 警告列表)
        """
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
        """验证基本设置"""
        project_name = config.get('PROJECT_NAME', 'crawlo')
        if not isinstance(project_name, str) or not project_name.strip():
            self.errors.append("PROJECT_NAME 必须是非空字符串")
    
    def _validate_network(self, config: Dict[str, Any]):
        """验证网络设置"""
        timeout = config.get('DOWNLOAD_TIMEOUT', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.errors.append("DOWNLOAD_TIMEOUT 必须是正数")
        
        delay = config.get('DOWNLOAD_DELAY', 1.0)
        if not isinstance(delay, (int, float)) or delay < 0:
            self.errors.append("DOWNLOAD_DELAY 必须是非负数")
        
        max_retries = config.get('MAX_RETRY_TIMES', 3)
        if not isinstance(max_retries, int) or max_retries < 0:
            self.errors.append("MAX_RETRY_TIMES 必须是非负整数")
        
        pool_limit = config.get('CONNECTION_POOL_LIMIT', 50)
        if not isinstance(pool_limit, int) or pool_limit <= 0:
            self.errors.append("CONNECTION_POOL_LIMIT 必须是正整数")
    
    def _validate_concurrency(self, config: Dict[str, Any]):
        """验证并发设置"""
        concurrency = config.get('CONCURRENCY', 8)
        if not isinstance(concurrency, int) or concurrency <= 0:
            self.errors.append("CONCURRENCY 必须是正整数")
        
        max_running = config.get('MAX_RUNNING_SPIDERS', 1)
        if not isinstance(max_running, int) or max_running <= 0:
            self.errors.append("MAX_RUNNING_SPIDERS 必须是正整数")
    
    def _validate_queue(self, config: Dict[str, Any]):
        """验证队列设置"""
        queue_type = config.get('QUEUE_TYPE', 'memory')
        valid_types = ['memory', 'redis', 'redis_stream', 'auto']
        if queue_type not in valid_types:
            self.errors.append(f"QUEUE_TYPE 必须是以下值之一: {valid_types}")
        
        max_size = config.get('SCHEDULER_MAX_QUEUE_SIZE', 2000)
        if not isinstance(max_size, int) or max_size <= 0:
            self.errors.append("SCHEDULER_MAX_QUEUE_SIZE 必须是正整数")
    
    def _validate_redis(self, config: Dict[str, Any]):
        """验证Redis设置"""
        if config.get('QUEUE_TYPE') == 'redis':
            host = config.get('REDIS_HOST', '127.0.0.1')
            if not isinstance(host, str) or not host.strip():
                self.errors.append("使用 Redis 模式时 REDIS_HOST 不能为空")
            
            port = config.get('REDIS_PORT', 6379)
            if not isinstance(port, int) or port <= 0 or port > 65535:
                self.errors.append("REDIS_PORT 必须是 1-65535 之间的整数")
    
    def _validate_logging(self, config: Dict[str, Any]):
        """验证日志设置"""
        level = config.get('LOG_LEVEL', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            self.errors.append(f"LOG_LEVEL 必须是以下值之一: {valid_levels}")


# ==================== 配置中心核心类 ====================

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
        """
        单机模式
        
        使用内存队列，无需外部依赖，适合开发和测试。
        
        Args:
            project_name: 项目名称
            **kwargs: 其他配置参数
            
        Returns:
            CrawloConfig 实例
        """
        settings = BASE_CONFIG.copy()
        settings.update(MODE_CONFIG_MAP['standalone'])
        settings['PROJECT_NAME'] = project_name
        settings.update({k.upper(): v for k, v in kwargs.items()})
        return cls(settings)
    
    @classmethod
    def distributed(cls, 
                     redis_host: str = '127.0.0.1',
                     redis_port: int = 6379,
                     redis_password: Optional[str] = None,
                     redis_username: Optional[str] = None,
                     redis_db: int = 0,
                     project_name: str = 'crawlo',
                     **kwargs) -> 'CrawloConfig':
        """
        分布式模式
        
        使用 Redis 队列，支持多节点扩展，适合大规模爬取。
        
        Args:
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            redis_password: Redis 密码
            redis_username: Redis 用户名（Redis 6.0+ ACL）
            redis_db: Redis 数据库编号
            project_name: 项目名称
            **kwargs: 其他配置参数
            
            Returns:
            CrawloConfig 实例
        """
        redis_cfg = RedisConfig(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            username=redis_username,
            db=redis_db
        )
        
        settings = BASE_CONFIG.copy()
        settings.update(MODE_CONFIG_MAP['distributed'])
        settings.update({
            'REDIS_HOST': redis_host,
            'REDIS_PORT': redis_port,
            'REDIS_PASSWORD': redis_password,
            'REDIS_USER': redis_username,
            'REDIS_DB': redis_db,
            'REDIS_URL': redis_cfg.to_url(),
            'PROJECT_NAME': project_name,
            'SCHEDULER_QUEUE_NAME': f'crawlo:{project_name}:queue:requests',
        })
        settings.update({k.upper(): v for k, v in kwargs.items()})
        return cls(settings)

    @classmethod
    def auto(cls, project_name: str = 'crawlo', **kwargs) -> 'CrawloConfig':
        """
        自动检测模式（推荐）
        
        运行时自动检测 Redis 可用性，智能选择最佳配置。
        
        Args:
            project_name: 项目名称
            **kwargs: 其他配置参数
            
        Returns:
            CrawloConfig 实例
        """
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
        """
        从环境变量加载配置
        
        支持的环境变量：
        - CRAWLO_MODE: 运行模式 (standalone/distributed/auto)
        - CRAWLO_REDIS_HOST: Redis 主机地址
        - CRAWLO_REDIS_PORT: Redis 端口
        - CRAWLO_REDIS_PASSWORD: Redis 密码
        - CRAWLO_REDIS_DB: Redis 数据库编号
        - CRAWLO_PROJECT_NAME: 项目名称
        - CRAWLO_CONCURRENCY: 并发数
        - CRAWLO_LOG_LEVEL: 日志级别
        
        Args:
            default_mode: 默认运行模式
            
        Returns:
            CrawloConfig 实例
        """
        # 环境变量配置映射
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
        
        kwargs = {}
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
        
        # 根据模式创建配置
        if mode == 'distributed':
            return cls.distributed(**kwargs)
        elif mode == 'auto':
            return cls.auto(**kwargs)
        return cls.standalone(**kwargs)
    
    def print_summary(self) -> 'CrawloConfig':
        """打印配置摘要（链式操作）"""
        print("\n" + "="*20 + " Crawlo Config Summary " + "="*20)
        print(f"Project: {self.get('PROJECT_NAME')}")
        print(f"Run Mode: {self.get('RUN_MODE')}")
        print(f"Concurrency: {self.get('CONCURRENCY')}")
        if self.get('REDIS_HOST'):
            print(f"Redis: {self.get('REDIS_HOST')}:{self.get('REDIS_PORT')}")
        print("="*63 + "\n")
        return self


# ==================== 便利函数 (向后兼容) ====================

def create_config(mode: str = 'standalone', **kwargs) -> CrawloConfig:
    """创建配置（向后兼容）"""
    if mode.lower() == 'standalone':
        return CrawloConfig.standalone(**kwargs)
    if mode.lower() == 'distributed':
        return CrawloConfig.distributed(**kwargs)
    if mode.lower() == 'auto':
        return CrawloConfig.auto(**kwargs)
    raise ValueError(f"Unknown mode: {mode}")


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """验证配置（向后兼容）"""
    return ConfigValidator().validate(config)


# 模式管理便利函数（向后兼容）
def standalone_mode(project_name: str = 'crawlo', **kwargs) -> Dict[str, Any]:
    """单机模式配置（向后兼容）"""
    return CrawloConfig.standalone(project_name, **kwargs).to_dict()


def distributed_mode(redis_host: str = '127.0.0.1', redis_port: int = 6379, 
                     project_name: str = 'crawlo', **kwargs) -> Dict[str, Any]:
    """分布式模式配置（向后兼容）"""
    return CrawloConfig.distributed(redis_host, redis_port, project_name=project_name, **kwargs).to_dict()


def auto_mode(project_name: str = 'crawlo', **kwargs) -> Dict[str, Any]:
    """自动检测模式配置（向后兼容）"""
    return CrawloConfig.auto(project_name, **kwargs).to_dict()


def from_env(default_mode: str = 'standalone') -> Dict[str, Any]:
    """从环境变量创建配置（向后兼容）"""
    return CrawloConfig.from_env(default_mode).to_dict()
