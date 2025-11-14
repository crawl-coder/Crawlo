#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 配置工厂
===============
提供优雅的配置方式，让用户能够轻松选择运行模式。

使用示例：
    # 单机模式（默认）
    config = CrawloConfig.standalone()
    
    # 分布式模式
    config = CrawloConfig.distributed(redis_host='192.168.1.100')
    
    # 自动检测模式
    config = CrawloConfig.auto()
    
    # 从环境变量
    config = CrawloConfig.from_env()
"""

from typing import Dict, Any, Optional


from crawlo.config_validator import validate_config
from crawlo.mode_manager import standalone_mode, distributed_mode, auto_mode, from_env
from crawlo.logging import get_logger


class CrawloConfig:
    """Crawlo 配置工厂类"""
    
    def __init__(self, settings: Dict[str, Any]) -> None:
        """
        初始化配置对象
        
        Args:
            settings: 配置字典
        """
        self.settings: Dict[str, Any] = settings
        self.logger = get_logger(self.__class__.__name__)
        # 验证配置
        self._validate_settings()
    
    def _validate_settings(self) -> None:
        """验证配置"""
        is_valid, errors, warnings = validate_config(self.settings)
        if not is_valid:
            error_msg = "配置验证失败:\n" + "\n".join([f"  - {error}" for error in errors])
            raise ValueError(error_msg)
        
        if warnings:
            warning_msg = "配置警告:\n" + "\n".join([f"  - {warning}" for warning in warnings])
            self.logger.warning(warning_msg)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> 'CrawloConfig':
        """
        设置配置项（链式调用）
        
        注意：设置后会自动验证配置合法性
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            self: 支持链式调用
        """
        self.settings[key] = value
        self._validate_settings()  # 自动验证
        return self
    
    def update(self, settings: Dict[str, Any]) -> 'CrawloConfig':
        """
        更新配置（链式调用）
        
        注意：更新后会自动验证配置合法性
        
        Args:
            settings: 配置字典
            
        Returns:
            self: 支持链式调用
        """
        self.settings.update(settings)
        self._validate_settings()  # 自动验证
        return self
    
    def set_concurrency(self, concurrency: int) -> 'CrawloConfig':
        """
        设置并发数
        
        Args:
            concurrency: 并发数
            
        Returns:
            self: 支持链式调用
        """
        return self.set('CONCURRENCY', concurrency)
    
    def set_delay(self, delay: float) -> 'CrawloConfig':
        """
        设置请求延迟
        
        Args:
            delay: 下载延迟（秒）
            
        Returns:
            self: 支持链式调用
        """
        return self.set('DOWNLOAD_DELAY', delay)
    
    def enable_debug(self) -> 'CrawloConfig':
        """
        启用调试模式
        
        Returns:
            self: 支持链式调用
        """
        return self.set('LOG_LEVEL', 'DEBUG')
    
    def enable_mysql(self) -> 'CrawloConfig':
        """
        启用 MySQL 存储
        
        Returns:
            self: 支持链式调用
        """
        pipelines = self.get('PIPELINES', [])
        if 'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline' not in pipelines:
            pipelines.append('crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline')
        return self.set('PIPELINES', pipelines)
    
    def set_redis_host(self, host: str) -> 'CrawloConfig':
        """
        设置 Redis 主机
        
        Args:
            host: Redis 主机地址
            
        Returns:
            self: 支持链式调用
        """
        return self.set('REDIS_HOST', host)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典的副本
        """
        return self.settings.copy()
    
    def print_summary(self) -> 'CrawloConfig':
        """
        打印配置摘要
        
        Returns:
            self: 支持链式调用
        """
        mode_info = {
            'memory': '单机模式',
            'redis': '分布式模式', 
            'auto': '自动检测模式'
        }
        
        queue_type = self.settings.get('QUEUE_TYPE', 'auto')
        filter_class = self.settings.get('FILTER_CLASS', '').split('.')[-1]
        concurrency = self.settings.get('CONCURRENCY', 8)
        
        print("=" * 50)
        print(f"Crawlo 配置摘要")
        print("=" * 50)
        print(f"运行模式: {mode_info.get(queue_type, queue_type)}")
        print(f"队列类型: {queue_type}")
        print(f"去重方式: {filter_class}")
        print(f"并发数量: {concurrency}")
        
        if queue_type == 'redis':
            redis_host = self.settings.get('REDIS_HOST', 'localhost')
            print(f"Redis 服务器: {redis_host}")
        
        print("=" * 50)
        return self
    
    def validate(self) -> bool:
        """
        验证当前配置
        
        Returns:
            bool: 配置是否有效
        """
        is_valid, errors, warnings = validate_config(self.settings)
        if not is_valid:
            print("配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        if warnings:
            print("配置警告:")
            for warning in warnings:
                print(f"  - {warning}")
        
        return True
    
    # ==================== 静态工厂方法 ====================
    
    @staticmethod
    def standalone(
        concurrency: int = 8,
        download_delay: float = 1.0,
        **kwargs: Any
    ) -> 'CrawloConfig':
        """
        创建单机模式配置
        
        Args:
            concurrency: 并发数
            download_delay: 下载延迟
            **kwargs: 其他配置项
            
        Returns:
            CrawloConfig: 配置对象
        """
        settings = standalone_mode(
            CONCURRENCY=concurrency,
            DOWNLOAD_DELAY=download_delay,
            **kwargs
        )
        return CrawloConfig(settings)
    
    @staticmethod
    def distributed(
        redis_host: str = '127.0.0.1',
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0,  # 添加 redis_db 参数
        project_name: str = 'crawlo',
        concurrency: int = 16,
        download_delay: float = 1.0,
        **kwargs: Any
    ) -> 'CrawloConfig':
        """
        创建分布式模式配置
        
        Args:
            redis_host: Redis 服务器地址
            redis_port: Redis 端口
            redis_password: Redis 密码
            redis_db: Redis 数据库编号
            project_name: 项目名称（用于命名空间）
            concurrency: 并发数
            download_delay: 下载延迟
            **kwargs: 其他配置项
            
        Returns:
            CrawloConfig: 配置对象
        """
        settings = distributed_mode(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            redis_db=redis_db,  # 传递 redis_db 参数
            project_name=project_name,
            CONCURRENCY=concurrency,
            DOWNLOAD_DELAY=download_delay,
            **kwargs
        )
        return CrawloConfig(settings)
    
    @staticmethod
    def auto(
        concurrency: int = 12,
        download_delay: float = 1.0,
        **kwargs: Any
    ) -> 'CrawloConfig':
        """
        创建自动检测模式配置
        
        Args:
            concurrency: 并发数
            download_delay: 下载延迟
            **kwargs: 其他配置项
            
        Returns:
            CrawloConfig: 配置对象
        """
        settings = auto_mode(
            CONCURRENCY=concurrency,
            DOWNLOAD_DELAY=download_delay,
            **kwargs
        )
        return CrawloConfig(settings)
    
    @staticmethod
    def from_env(default_mode: str = 'standalone') -> 'CrawloConfig':
        """
        从环境变量创建配置
        
        支持的环境变量：
        - CRAWLO_MODE: 运行模式 (standalone/distributed/auto)
        - REDIS_HOST: Redis 主机
        - REDIS_PORT: Redis 端口
        - REDIS_PASSWORD: Redis 密码
        - CONCURRENCY: 并发数
        - PROJECT_NAME: 项目名称
        
        Args:
            default_mode: 默认运行模式
            
        Returns:
            CrawloConfig: 配置对象
        """
        settings = from_env(default_mode)
        return CrawloConfig(settings)
    
    @staticmethod
    def custom(settings: Dict[str, Any]) -> 'CrawloConfig':
        """
        创建自定义配置
        
        Args:
            settings: 自定义配置字典
            
        Returns:
            CrawloConfig: 配置对象
        """
        return CrawloConfig(settings)
    
    @staticmethod
    def presets() -> 'Presets':
        """
        获取预设配置对象
        
        Returns:
            Presets: 预设配置对象
        """
        return Presets()


# ==================== 便利函数 ====================

def create_config(
    mode: str = 'standalone',
    **kwargs: Any
) -> CrawloConfig:
    """
    便利函数：创建配置
    
    Args:
        mode: 运行模式 ('standalone', 'distributed', 'auto')
        **kwargs: 配置参数
        
    Returns:
        CrawloConfig: 配置对象
    """
    if mode.lower() == 'standalone':
        return CrawloConfig.standalone(**kwargs)
    elif mode.lower() == 'distributed':
        return CrawloConfig.distributed(**kwargs)
    elif mode.lower() == 'auto':
        return CrawloConfig.auto(**kwargs)
    else:
        raise ValueError(f"不支持的运行模式: {mode}")


# ==================== 预设配置 ====================

class Presets:
    """预设配置类"""
    
    @staticmethod
    def development() -> CrawloConfig:
        """
        开发环境配置
        
        Returns:
            CrawloConfig: 开发环境配置对象
        """
        return CrawloConfig.standalone(
            concurrency=4,
            download_delay=2.0,
            LOG_LEVEL='DEBUG',
            STATS_DUMP=True
        )
    
    @staticmethod
    def production() -> CrawloConfig:
        """
        生产环境配置
        
        Returns:
            CrawloConfig: 生产环境配置对象
        """
        return CrawloConfig.auto(
            concurrency=16,
            download_delay=1.0,
            LOG_LEVEL='INFO',
            RETRY_TIMES=5
        )
    
    @staticmethod
    def large_scale(redis_host: str, project_name: str) -> CrawloConfig:
        """
        大规模分布式配置
        
        Args:
            redis_host: Redis 主机地址
            project_name: 项目名称
            
        Returns:
            CrawloConfig: 大规模分布式配置对象
        """
        return CrawloConfig.distributed(
            redis_host=redis_host,
            project_name=project_name,
            concurrency=32,
            download_delay=0.5,
            SCHEDULER_MAX_QUEUE_SIZE=10000,
            LARGE_SCALE_BATCH_SIZE=2000
        )
    
    @staticmethod
    def gentle() -> CrawloConfig:
        """
        温和模式配置（避免被封）
        
        Returns:
            CrawloConfig: 温和模式配置对象
        """
        return CrawloConfig.standalone(
            concurrency=2,
            download_delay=3.0,
            RANDOMNESS=True,
            RANDOM_RANGE=(2.0, 5.0)
        )