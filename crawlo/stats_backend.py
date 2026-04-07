#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统计后端模块
============
提供可插拔的统计后端接口，支持多种存储后端。

核心组件：
- StatsBackend: 统计后端抽象基类
- MemoryStatsBackend: 内存存储后端（默认）
- RedisStatsBackend: Redis 存储后端
- StatsBackendFactory: 后端工厂

使用示例：
    # 使用默认内存后端
    stats = StatsCollector()
    
    # 使用 Redis 后端
    stats = StatsCollector(backend=RedisStatsBackend(redis_client))
    
    # 通过配置选择后端
    STAT_BACKEND = 'redis'
    STAT_REDIS_KEY = 'crawlo:stats'
"""
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, Optional

from crawlo.logging import get_logger


class StatsBackend(ABC):
    """
    统计后端抽象基类
    
    定义统计存储的标准接口，所有后端实现都应继承此类。
    
    使用示例：
        class MyStatsBackend(StatsBackend):
            def inc_value(self, key: str, count: int = 1) -> None:
                # 自定义实现
                pass
    """
    
    @abstractmethod
    def inc_value(self, key: str, count: int = 1) -> None:
        """
        增加计数器值
        
        Args:
            key: 统计键名
            count: 增量，默认为 1
        """
        pass
    
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取统计值
        
        Args:
            key: 统计键名
            default: 默认值
            
        Returns:
            Any: 统计值
        """
        pass
    
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        """
        设置统计值
        
        Args:
            key: 统计键名
            value: 统计值
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取所有统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空所有统计信息"""
        pass
    
    def max_value(self, key: str, value: Any) -> None:
        """
        设置最大值
        
        Args:
            key: 统计键名
            value: 值
        """
        current = self.get_value(key)
        if current is None or value > current:
            self.set_value(key, value)
    
    def min_value(self, key: str, value: Any) -> None:
        """
        设置最小值
        
        Args:
            key: 统计键名
            value: 值
        """
        current = self.get_value(key)
        if current is None or value < current:
            self.set_value(key, value)
    
    def append_value(self, key: str, value: Any) -> None:
        """
        追加值到列表
        
        Args:
            key: 统计键名
            value: 值
        """
        current = self.get_value(key, [])
        if not isinstance(current, list):
            current = [current]
        current.append(value)
        self.set_value(key, current)
    
    def has_key(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 统计键名
            
        Returns:
            bool: 是否存在
        """
        return self.get_value(key) is not None
    
    def close(self) -> None:
        """关闭后端（可选实现）"""
        pass


class MemoryStatsBackend(StatsBackend):
    """
    内存存储后端
    
    使用 Python 字典存储统计信息。
    适合单机模式或不需要持久化的场景。
    
    特性：
    - 快速访问
    - 无持久化
    - 线程安全（使用 defaultdict）
    """
    
    def __init__(self, prefix: str = ""):
        """
        初始化内存后端
        
        Args:
            prefix: 键前缀（用于命名空间隔离）
        """
        self._prefix = prefix
        self._stats: Dict[str, Any] = defaultdict(int)
        self._logger = get_logger(self.__class__.__name__)
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        if self._prefix:
            return f"{self._prefix}:{key}"
        return key
    
    def inc_value(self, key: str, count: int = 1) -> None:
        full_key = self._make_key(key)
        if full_key not in self._stats:
            self._stats[full_key] = 0
        self._stats[full_key] += count
    
    def get_value(self, key: str, default: Any = None) -> Any:
        full_key = self._make_key(key)
        return self._stats.get(full_key, default)
    
    def set_value(self, key: str, value: Any) -> None:
        full_key = self._make_key(key)
        self._stats[full_key] = value
    
    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)
    
    def clear(self) -> None:
        self._stats.clear()


class RedisStatsBackend(StatsBackend):
    """
    Redis 存储后端
    
    使用 Redis 存储统计信息。
    适合分布式模式，支持多进程共享统计。
    
    特性：
    - 分布式共享
    - 持久化支持
    - 高性能
    
    使用示例：
        import redis
        client = redis.Redis(host='localhost', port=6379)
        backend = RedisStatsBackend(client, key='crawlo:stats')
    """
    
    def __init__(
        self, 
        redis_client, 
        key: str = "crawlo:stats",
        expire: Optional[int] = None
    ):
        """
        初始化 Redis 后端
        
        Args:
            redis_client: Redis 客户端实例
            key: Redis 键名
            expire: 过期时间（秒），None 表示不过期
        """
        self._redis = redis_client
        self._key = key
        self._expire = expire
        self._logger = get_logger(self.__class__.__name__)
    
    def inc_value(self, key: str, count: int = 1) -> None:
        try:
            self._redis.hincrby(self._key, key, count)
        except Exception as e:
            self._logger.error(f"Redis hincrby error: {e}")
    
    def get_value(self, key: str, default: Any = None) -> Any:
        try:
            value = self._redis.hget(self._key, key)
            if value is None:
                return default
            # 尝试解析为数字
            try:
                if '.' in value.decode():
                    return float(value)
                return int(value)
            except (ValueError, AttributeError):
                return value.decode() if isinstance(value, bytes) else value
        except Exception as e:
            self._logger.error(f"Redis hget error: {e}")
            return default
    
    def set_value(self, key: str, value: Any) -> None:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self._redis.hset(self._key, key, value)
            if self._expire:
                self._redis.expire(self._key, self._expire)
        except Exception as e:
            self._logger.error(f"Redis hset error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        try:
            data = self._redis.hgetall(self._key)
            result = {}
            for k, v in data.items():
                key = k.decode() if isinstance(k, bytes) else k
                val = v.decode() if isinstance(v, bytes) else v
                # 尝试解析数字
                try:
                    if '.' in val:
                        result[key] = float(val)
                    else:
                        result[key] = int(val)
                except (ValueError, TypeError):
                    result[key] = val
            return result
        except Exception as e:
            self._logger.error(f"Redis hgetall error: {e}")
            return {}
    
    def clear(self) -> None:
        try:
            self._redis.delete(self._key)
        except Exception as e:
            self._logger.error(f"Redis delete error: {e}")
    
    def close(self) -> None:
        """关闭 Redis 连接（可选）"""
        pass


class FileStatsBackend(StatsBackend):
    """
    文件存储后端
    
    使用 JSON 文件存储统计信息。
    适合需要持久化但不需要分布式的场景。
    """
    
    def __init__(self, file_path: str = "stats.json"):
        """
        初始化文件后端
        
        Args:
            file_path: 文件路径
        """
        self._file_path = file_path
        self._stats: Dict[str, Any] = {}
        self._logger = get_logger(self.__class__.__name__)
        self._load()
    
    def _load(self) -> None:
        """从文件加载统计信息"""
        import os
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    self._stats = json.load(f)
            except Exception as e:
                self._logger.warning(f"Failed to load stats from file: {e}")
                self._stats = {}
    
    def _save(self) -> None:
        """保存统计信息到文件"""
        try:
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(self._stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._logger.error(f"Failed to save stats to file: {e}")
    
    def inc_value(self, key: str, count: int = 1) -> None:
        if key not in self._stats:
            self._stats[key] = 0
        self._stats[key] += count
        self._save()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        return self._stats.get(key, default)
    
    def set_value(self, key: str, value: Any) -> None:
        self._stats[key] = value
        self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)
    
    def clear(self) -> None:
        self._stats.clear()
        self._save()


class StatsBackendFactory:
    """
    统计后端工厂
    
    根据配置创建合适的后端实例。
    
    使用示例：
        # 从配置创建
        backend = StatsBackendFactory.from_settings(settings)
        
        # 按类型创建
        backend = StatsBackendFactory.create('memory')
        backend = StatsBackendFactory.create('redis', redis_client=client)
    """
    
    _backends = {
        'memory': MemoryStatsBackend,
        'redis': RedisStatsBackend,
        'file': FileStatsBackend,
    }
    
    @classmethod
    def register(cls, name: str, backend_class: type) -> None:
        """
        注册自定义后端
        
        Args:
            name: 后端名称
            backend_class: 后端类
        """
        cls._backends[name] = backend_class
    
    @classmethod
    def create(
        cls, 
        backend_type: str = 'memory',
        **kwargs
    ) -> StatsBackend:
        """
        创建后端实例
        
        Args:
            backend_type: 后端类型
            **kwargs: 传递给后端构造函数的参数
            
        Returns:
            StatsBackend: 后端实例
        """
        if backend_type not in cls._backends:
            raise ValueError(
                f"Unknown stats backend type: {backend_type}. "
                f"Available types: {list(cls._backends.keys())}"
            )
        
        backend_class = cls._backends[backend_type]
        return backend_class(**kwargs)
    
    @classmethod
    def from_settings(cls, settings) -> StatsBackend:
        """
        从配置创建后端
        
        Args:
            settings: 配置对象
            
        Returns:
            StatsBackend: 后端实例
        """
        backend_type = settings.get('STATS_BACKEND', 'memory')
        
        if backend_type == 'memory':
            return MemoryStatsBackend(
                prefix=settings.get('STATS_PREFIX', '')
            )
        
        elif backend_type == 'redis':
            # 尝试获取 Redis 客户端
            redis_url = settings.get('REDIS_URL')
            redis_host = settings.get('REDIS_HOST', 'localhost')
            redis_port = settings.get_int('REDIS_PORT', 6379)
            redis_db = settings.get_int('REDIS_DB', 0)
            redis_password = settings.get('REDIS_PASSWORD')
            
            try:
                import redis
                if redis_url:
                    client = redis.from_url(redis_url)
                else:
                    client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password
                    )
                return RedisStatsBackend(
                    client,
                    key=settings.get('STATS_REDIS_KEY', 'crawlo:stats'),
                    expire=settings.get_int('STATS_REDIS_EXPIRE', None)
                )
            except ImportError:
                get_logger(cls.__name__).warning(
                    "Redis backend requested but redis not installed, "
                    "falling back to memory backend"
                )
                return MemoryStatsBackend()
        
        elif backend_type == 'file':
            return FileStatsBackend(
                file_path=settings.get('STATS_FILE', 'stats.json')
            )
        
        else:
            # 尝试自定义后端
            return cls.create(backend_type)


# ==================== 导出 ====================

__all__ = [
    'StatsBackend',
    'MemoryStatsBackend',
    'RedisStatsBackend',
    'FileStatsBackend',
    'StatsBackendFactory',
]
