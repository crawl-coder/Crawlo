#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
队列配置辅助工具
为用户提供简洁的队列配置接口
"""
from typing import Dict, Any, Optional


class QueueHelper:
    """队列配置辅助类"""
    
    @staticmethod
    def use_memory_queue(max_size: int = 2000) -> Dict[str, Any]:
        """
        配置使用内存队列
        
        Args:
            max_size: 队列最大容量
            
        Returns:
            配置字典
        """
        return {
            'QUEUE_TYPE': 'memory',
            'SCHEDULER_MAX_QUEUE_SIZE': max_size,
        }
    
    @staticmethod
    def use_redis_queue(
        host: str = "127.0.0.1",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        queue_name: str = "crawlo:requests",
        max_retries: int = 3,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        配置使用 Redis 分布式队列
        
        Args:
            host: Redis 主机地址
            port: Redis 端口
            password: Redis 密码（可选）
            db: Redis 数据库编号
            queue_name: 队列名称
            max_retries: 最大重试次数
            timeout: 操作超时时间（秒）
            
        Returns:
            配置字典
        """
        if password:
            redis_url = f"redis://:{password}@{host}:{port}/{db}"
        else:
            redis_url = f"redis://{host}:{port}/{db}"
        
        return {
            'QUEUE_TYPE': 'redis',
            'REDIS_URL': redis_url,
            'REDIS_HOST': host,
            'REDIS_PORT': port,
            'REDIS_PASSWORD': password or '',
            'REDIS_DB': db,
            'SCHEDULER_QUEUE_NAME': queue_name,
            'QUEUE_MAX_RETRIES': max_retries,
            'QUEUE_TIMEOUT': timeout,
        }
    
    @staticmethod
    def auto_queue(
        redis_fallback: bool = True,
        memory_max_size: int = 2000,
        **redis_kwargs
    ) -> Dict[str, Any]:
        """
        配置自动选择队列类型
        
        Args:
            redis_fallback: Redis 不可用时是否回退到内存队列
            memory_max_size: 内存队列最大容量
            **redis_kwargs: Redis 配置参数
            
        Returns:
            配置字典
        """
        config = {
            'QUEUE_TYPE': 'auto',
            'SCHEDULER_MAX_QUEUE_SIZE': memory_max_size,
        }
        
        # 添加 Redis 配置（用于自动检测）
        if redis_kwargs:
            redis_config = QueueHelper.use_redis_queue(**redis_kwargs)
            config.update(redis_config)
            config['QUEUE_TYPE'] = 'auto'  # 确保是自动模式
        
        return config


# 预定义的常用配置
class QueuePresets:
    """预定义的队列配置"""
    
    # 开发环境：使用内存队列
    DEVELOPMENT = QueueHelper.use_memory_queue(max_size=1000)
    
    # 生产环境：使用 Redis 分布式队列
    PRODUCTION = QueueHelper.use_redis_queue(
        host="127.0.0.1",
        port=6379,
        queue_name="crawlo:production",
        max_retries=5,
        timeout=600
    )
    
    # 测试环境：自动选择，Redis 不可用时使用内存队列
    TESTING = QueueHelper.auto_queue(
        redis_fallback=True,
        memory_max_size=500,
        host="127.0.0.1",
        port=6379,
        queue_name="crawlo:testing"
    )
    
    # 高性能环境：Redis 集群
    HIGH_PERFORMANCE = QueueHelper.use_redis_queue(
        host="redis-cluster.example.com",
        port=6379,
        queue_name="crawlo:cluster",
        max_retries=10,
        timeout=300
    )


def apply_queue_config(settings_dict: Dict[str, Any], config: Dict[str, Any]) -> None:
    """
    将队列配置应用到设置字典
    
    Args:
        settings_dict: 现有的设置字典
        config: 队列配置字典
    """
    settings_dict.update(config)


# 使用示例和文档
USAGE_EXAMPLES = """
# 使用示例：

# 1. 在 settings.py 中使用内存队列
from crawlo.utils.queue_helper import QueueHelper
apply_queue_config(locals(), QueueHelper.use_memory_queue())

# 2. 在 settings.py 中使用 Redis 队列
apply_queue_config(locals(), QueueHelper.use_redis_queue(
    host="redis.example.com",
    password="your_password"
))

# 3. 使用预定义配置
from crawlo.utils.queue_helper import QueuePresets
apply_queue_config(locals(), QueuePresets.PRODUCTION)

# 4. 自动选择队列类型
apply_queue_config(locals(), QueueHelper.auto_queue(
    host="127.0.0.1",
    port=6379
))

# 5. 直接在 settings 中配置
QUEUE_TYPE = 'auto'  # 'memory', 'redis', 'auto'
REDIS_URL = 'redis://127.0.0.1:6379/0'
SCHEDULER_MAX_QUEUE_SIZE = 2000
"""