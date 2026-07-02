#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统计后端实现
============
提供多种统计存储后端：内存、Redis、文件。

核心组件：
- StatsBackend: 统计后端抽象基类
- MemoryStatsBackend: 内存存储后端（默认）
- RedisStatsBackend: Redis 存储后端
- FileStatsBackend: 文件存储后端
- StatsBackendFactory: 后端工厂
"""
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, Optional

from crawlo.logging import get_logger


# ==================== 统计后端抽象基类 ====================

class StatsBackend(ABC):
    """统计后端抽象基类"""
    
    @abstractmethod
    def inc_value(self, key: str, count: int = 1) -> None:
        pass
    
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        pass
    
    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def clear(self) -> None:
        pass
    
    def max_value(self, key: str, value: Any) -> None:
        """设置最大值"""
        current = self.get_value(key)
        if current is None or value > current:
            self.set_value(key, value)
    
    def min_value(self, key: str, value: Any) -> None:
        """设置最小值"""
        current = self.get_value(key)
        if current is None or value < current:
            self.set_value(key, value)
    
    def append_value(self, key: str, value: Any) -> None:
        """追加值到列表"""
        current = self.get_value(key, [])
        if not isinstance(current, list):
            current = [current]
        current.append(value)
        self.set_value(key, current)
    
    def has_key(self, key: str) -> bool:
        """检查键是否存在"""
        return self.get_value(key) is not None
    
    def close(self) -> None:
        """关闭后端（可选实现）"""
        pass


# ==================== 内存后端 ====================

class MemoryStatsBackend(StatsBackend):
    """内存存储后端（默认）"""
    
    def __init__(self, prefix: str = ""):
        self._prefix = prefix
        self._stats: Dict[str, Any] = defaultdict(int)
        self._logger = get_logger(self.__class__.__name__)
    
    def _make_key(self, key: str) -> str:
        """生成完整键名"""
        return f"{self._prefix}:{key}" if self._prefix else key
    
    def inc_value(self, key: str, count: int = 1) -> None:
        full_key = self._make_key(key)
        self._stats[full_key] += count  # defaultdict(int) 自动初始化为 0
    
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


# ==================== Redis 后端 ====================

class RedisStatsBackend(StatsBackend):
    """Redis 存储后端"""
    
    def __init__(self, redis_client, key: str = "crawlo:stats", expire: Optional[int] = None):
        self._redis = redis_client
        self._key = key
        self._expire = expire
        self._logger = get_logger(self.__class__.__name__)
    
    @staticmethod
    def _parse_value(value: Any) -> Any:
        """统一值解析逻辑"""
        if isinstance(value, bytes):
            value = value.decode()
        
        # 先尝试 JSON 解析（处理列表、字典、布尔值、null）
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 再尝试数字解析
        try:
            return float(value) if '.' in value else int(value)
        except (ValueError, TypeError):
            return value
    
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
            return self._parse_value(value)
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
                result[key] = self._parse_value(v)
            return result
        except Exception as e:
            self._logger.error(f"Redis hgetall error: {e}")
            return {}
    
    def clear(self) -> None:
        try:
            self._redis.delete(self._key)
        except Exception as e:
            self._logger.error(f"Redis delete error: {e}")


# ==================== 文件后端 ====================

class FileStatsBackend(StatsBackend):
    """文件存储后端"""
    
    def __init__(self, file_path: str = "stats.json", auto_save: bool = False):
        self._file_path = file_path
        self._auto_save = auto_save  # 默认关闭自动保存，减少 I/O
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
    
    def _save(self) -> None:
        """保存统计信息到文件"""
        try:
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(self._stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._logger.error(f"Failed to save stats to file: {e}")
    
    def inc_value(self, key: str, count: int = 1) -> None:
        self._stats[key] = self._stats.get(key, 0) + count
        if self._auto_save:
            self._save()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        return self._stats.get(key, default)
    
    def set_value(self, key: str, value: Any) -> None:
        self._stats[key] = value
        if self._auto_save:
            self._save()
    
    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)
    
    def clear(self) -> None:
        self._stats.clear()
        if self._auto_save:
            self._save()
    
    def flush(self) -> None:
        """强制保存统计信息到文件"""
        self._save()
    
    def close(self) -> None:
        """关闭后端时确保保存"""
        self._save()


# ==================== 后端工厂 ====================

class StatsBackendFactory:
    """统计后端工厂"""
    
    _backends = {
        'memory': MemoryStatsBackend,
        'redis': RedisStatsBackend,
        'file': FileStatsBackend,
    }
    
    @classmethod
    def create(cls, backend_type: str = 'memory', **kwargs) -> StatsBackend:
        """创建指定类型的后端"""
        if backend_type not in cls._backends:
            raise ValueError(f"Unknown stats backend type: {backend_type}")
        return cls._backends[backend_type](**kwargs)
    
    @classmethod
    def from_settings(cls, settings) -> StatsBackend:
        """从配置创建后端"""
        backend_type = settings.get('STATS_BACKEND', 'memory')
        
        if backend_type == 'memory':
            return MemoryStatsBackend(prefix=settings.get('STATS_PREFIX', ''))
        
        elif backend_type == 'redis':
            redis_url = settings.get('REDIS_URL')
            try:
                # 优先使用异步 Redis 客户端
                try:
                    import redis.asyncio as aioredis
                    client = aioredis.from_url(redis_url) if redis_url else aioredis.Redis(
                        host=settings.get('REDIS_HOST', 'localhost'),
                        port=settings.get_int('REDIS_PORT', 6379),
                        db=settings.get_int('REDIS_DB', 0),
                        password=settings.get('REDIS_PASSWORD')
                    )
                except ImportError:
                    # 回退到同步客户端
                    import redis
                    client = redis.from_url(redis_url) if redis_url else redis.Redis(
                        host=settings.get('REDIS_HOST', 'localhost'),
                        port=settings.get_int('REDIS_PORT', 6379),
                        db=settings.get_int('REDIS_DB', 0),
                        password=settings.get('REDIS_PASSWORD')
                    )
                    get_logger(cls.__name__).warning(
                        "redis.asyncio not available, using synchronous Redis client"
                    )
                
                return RedisStatsBackend(
                    client, 
                    key=settings.get('STATS_REDIS_KEY', 'crawlo:stats'),
                    expire=settings.get_int('STATS_REDIS_EXPIRE', None)
                )
            except ImportError:
                get_logger(cls.__name__).warning("redis not installed, fallback to memory backend")
                return MemoryStatsBackend()
        
        elif backend_type == 'file':
            return FileStatsBackend(file_path=settings.get('STATS_FILE', 'stats.json'))

        elif backend_type == 'prometheus':
            try:
                from crawlo.stats.prometheus_backend import PrometheusStatsBackend

                import os
                import socket
                worker_id = (
                    settings.get('WORKER_ID')
                    or f"{socket.gethostname()}-{os.getpid()}"
                )
                return PrometheusStatsBackend(
                    prefix=settings.get('STATS_PREFIX', 'crawlo'),
                    port=settings.get_int('PROMETHEUS_METRICS_PORT', 9100),
                    labels={
                        'spider': settings.get('PROJECT_NAME', 'crawlo'),
                        'worker_id': worker_id,
                        **settings.get_dict('PROMETHEUS_LABELS', {}),
                    },
                )
            except ImportError as e:
                get_logger(cls.__name__).warning(
                    f"prometheus-client not installed, fallback to memory backend: {e}"
                )
                return MemoryStatsBackend()

        return MemoryStatsBackend()
