#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2026-04-07
# @Author  : crawl-coder
# @Desc    : 指纹存储后端

提供 SQLite（单机）和 Redis（分布式）两种存储后端。

核心设计：
- 按 domain + identifier 分区存储
- 同 domain+identifier 的指纹覆盖更新
- 线程安全（SQLite 使用 RLock，Redis 天然线程安全）
- SQLite 使用 WAL 模式提升并发性能
"""
import json
import os
from abc import ABC, abstractmethod
from hashlib import sha256
from threading import RLock
from typing import Dict, Optional, Any

from crawlo.logging import get_logger
from .element_fingerprint import ElementFingerprint, extract_domain_from_url


class StorageBackend(ABC):
    """指纹存储后端抽象基类"""

    @abstractmethod
    def save(self, domain: str, identifier: str, fingerprint: ElementFingerprint) -> None:
        """保存元素指纹

        Args:
            domain: 域名（分区键）
            identifier: 标识符（通常为选择器字符串）
            fingerprint: 元素指纹
        """
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, domain: str, identifier: str) -> Optional[Dict]:
        """加载元素指纹数据

        Args:
            domain: 域名
            identifier: 标识符

        Returns:
            Optional[Dict]: 指纹字典，不存在返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """关闭存储连接"""
        pass


class SqliteStorage(StorageBackend):
    """SQLite 存储后端（单机模式）

    SQLite 存储后端：
    - 线程安全（RLock + WAL 模式）
    - 按 domain + identifier 分区
    - 同 key 覆盖更新
    """

    def __init__(self, storage_file: str = 'adaptive_fingerprints.db'):
        self.storage_file = storage_file
        self.lock = RLock()
        self.logger = get_logger(self.__class__.__name__)

        # 确保目录存在
        db_dir = os.path.dirname(storage_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # 初始化数据库
        self._connection = self._create_connection()
        self._setup_database()

    def _create_connection(self):
        """创建 SQLite 连接"""
        from sqlite3 import connect as db_connect
        conn = db_connect(self.storage_file, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _setup_database(self) -> None:
        """创建存储表"""
        with self.lock:
            cursor = self._connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_fingerprints (
                    id INTEGER PRIMARY KEY,
                    domain TEXT,
                    identifier TEXT,
                    fingerprint_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (domain, identifier)
                )
            """)
            self._connection.commit()

    def save(self, domain: str, identifier: str, fingerprint: ElementFingerprint) -> None:
        """保存元素指纹"""
        data = fingerprint.to_dict()
        with self.lock:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO adaptive_fingerprints (domain, identifier, fingerprint_data)
                VALUES (?, ?, ?)
                """,
                (domain, identifier, json.dumps(data, ensure_ascii=False)),
            )
            self._connection.commit()
            self.logger.debug(f"Saved fingerprint: domain={domain}, identifier={identifier}")

    def retrieve(self, domain: str, identifier: str) -> Optional[Dict]:
        """加载元素指纹数据"""
        with self.lock:
            cursor = self._connection.cursor()
            cursor.execute(
                "SELECT fingerprint_data FROM adaptive_fingerprints WHERE domain = ? AND identifier = ?",
                (domain, identifier),
            )
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None

    def close(self) -> None:
        """关闭连接"""
        with self.lock:
            if self._connection:
                self._connection.commit()
                self._connection.close()
                self._connection = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass  # 解释器退出时 sqlite3 可能已卸载


class RedisStorage(StorageBackend):
    """Redis 存储后端（分布式模式）

    使用 Redis Hash 存储指纹数据，key 格式：crawlo:adaptive:{domain}
    """

    def __init__(self, redis_url: str = 'redis://localhost:6379/0', redis_client=None):
        self.logger = get_logger(self.__class__.__name__)
        self._redis = redis_client
        self._redis_url = redis_url

        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
            except ImportError:
                raise ImportError(
                    "Redis storage requires the 'redis' package. "
                    "Install it with: pip install redis"
                )

    def _make_key(self, domain: str) -> str:
        """生成 Redis key"""
        return f"crawlo:adaptive:{domain}"

    @staticmethod
    def _make_hash_key(identifier: str) -> str:
        """生成 Hash field（对长选择器做哈希缩短）"""
        return sha256(identifier.encode('utf-8')).hexdigest()[:32]

    def save(self, domain: str, identifier: str, fingerprint: ElementFingerprint) -> None:
        """保存元素指纹"""
        key = self._make_key(domain)
        field = self._make_hash_key(identifier)
        data = json.dumps(fingerprint.to_dict(), ensure_ascii=False)
        # 同时存储 identifier 映射，便于调试
        self._redis.hset(key, mapping={
            field: data,
            f"{field}__selector": identifier,
        })
        self.logger.debug(f"Saved fingerprint: domain={domain}, identifier={identifier}")

    def retrieve(self, domain: str, identifier: str) -> Optional[Dict]:
        """加载元素指纹数据"""
        key = self._make_key(domain)
        field = self._make_hash_key(identifier)
        data = self._redis.hget(key, field)
        if data:
            return json.loads(data)
        return None

    def close(self) -> None:
        """Redis 连接通常由连接池管理，无需手动关闭"""
        pass


class FingerprintStorage:
    """指纹存储管理器 - 统一接口

    根据配置自动选择存储后端，提供统一的 save/retrieve 接口。
    对外隐藏 domain 提取逻辑，调用方只需传入 url。
    集成了内存缓存层以优化频繁读取性能。
    """

    def __init__(
        self,
        backend: str = 'sqlite',
        storage_file: str = 'adaptive_fingerprints.db',
        redis_url: str = '',
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_password: str = '',
        redis_db: int = 0,
        redis_client=None,
        cache_size: int = 128,
    ):
        """
        Args:
            backend: 存储后端类型，'sqlite' 或 'redis'
            storage_file: SQLite 数据库文件路径
            redis_url: Redis 连接 URL（优先使用，为空则从各字段构建）
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            redis_password: Redis 密码
            redis_db: Redis 数据库编号
            redis_client: 可选的 Redis 客户端实例
            cache_size: 内存 LRU 缓存大小
        """
        self.logger = get_logger(self.__class__.__name__)

        if backend == 'sqlite':
            self._backend = SqliteStorage(storage_file)
        elif backend == 'redis':
            # 优先使用完整的 redis_url，否则从各字段构建
            if not redis_url:
                if redis_password:
                    redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}'
                else:
                    redis_url = f'redis://{redis_host}:{redis_port}/{redis_db}'
            self._backend = RedisStorage(redis_url, redis_client)
        else:
            raise ValueError(f"Unknown storage backend: {backend}, expected 'sqlite' or 'redis'")

        # 内存 LRU 缓存层
        from collections import OrderedDict
        self._cache = OrderedDict()
        self._cache_size = cache_size
        self._cache_lock = RLock()

        self.logger.debug(f"FingerprintStorage initialized with backend: {backend} (cache_size={cache_size})")

    def save(self, url: str, identifier: str, fingerprint: ElementFingerprint) -> None:
        """保存元素指纹并更新缓存"""
        domain = extract_domain_from_url(url)
        
        # 先保存到后端
        self._backend.save(domain, identifier, fingerprint)
        
        # 更新缓存
        cache_key = (domain, identifier)
        with self._cache_lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
            self._cache[cache_key] = fingerprint.to_dict()
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)

    def retrieve(self, url: str, identifier: str) -> Optional[Dict]:
        """加载元素指纹数据（优先查询缓存）"""
        domain = extract_domain_from_url(url)
        cache_key = (domain, identifier)

        # 1. 尝试从缓存获取
        with self._cache_lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                self.logger.debug(f"Cache hit: {domain}:{identifier}")
                return self._cache[cache_key]

        # 2. 从后端加载
        data = self._backend.retrieve(domain, identifier)
        
        # 3. 填充缓存
        if data:
            with self._cache_lock:
                self._cache[cache_key] = data
                if len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
        
        return data

    def clear_cache(self) -> None:
        """清空内存缓存"""
        with self._cache_lock:
            self._cache.clear()

    def close(self) -> None:
        """关闭存储"""
        self._backend.close()
        self.clear_cache()
