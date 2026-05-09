#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
磁盘持久化队列实现

基于 SQLite 的磁盘持久化队列，
支持大规模数据存储、断电恢复和批量操作。
"""
import asyncio
import os
import json
import time
import logging
import pickle
import sqlite3
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Any, Dict, List, TYPE_CHECKING
from contextlib import contextmanager
from dataclasses import dataclass

from crawlo.queue.interfaces import IQueue, BackpressureableQueueMixin
from crawlo.queue.queue_types import QueueType

if TYPE_CHECKING:
    from crawlo.network.request import Request

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """队列项数据类"""
    id: int
    priority: int
    data: bytes  # 序列化的数据
    created_at: float
    metadata: Optional[str] = None


class DiskQueueConfig:
    """磁盘队列配置"""
    
    def __init__(
        self,
        path: str = None,
        name: str = "disk_queue",
        max_size: int = 0,
        db_name: str = "queue.db",
        table_name: str = "queue_items",
        max_connections: int = 5,
        WAL_mode: bool = True,
        cache_size: int = 10000,
        synchronous: str = "NORMAL",
        batch_size: int = 100,
        cleanup_interval: float = 300.0,
        ttl: float = 0,  # 0 表示永不过期
        serialization: str = "pickle",
        compress: bool = False,
    ):
        """
        初始化磁盘队列配置
        
        Args:
            path: 数据库文件目录
            name: 队列名称（用于生成数据库文件路径）
            max_size: 最大队列大小，0 表示无限制
            db_name: 数据库文件名
            table_name: 表名
            max_connections: 最大连接数
            WAL_mode: 是否启用 WAL 模式
            cache_size: 缓存大小
            synchronous: 同步模式 (OFF, NORMAL, FULL)
            batch_size: 批量操作大小
            cleanup_interval: 清理间隔（秒）
            ttl: 生存时间（秒），0 表示永不过期
            serialization: 序列化方式 ("pickle", "json")
            compress: 是否压缩数据
        """
        if path is None:
            path = os.path.join(tempfile.gettempdir(), "crawlo_disk_queue")
        
        self.path = path
        self.name = name
        self.max_size = max_size
        self.db_name = db_name
        self.table_name = table_name
        self.max_connections = max_connections
        self.WAL_mode = WAL_mode
        self.cache_size = cache_size
        self.synchronous = synchronous
        self.batch_size = batch_size
        self.cleanup_interval = cleanup_interval
        self.ttl = ttl
        self.serialization = serialization
        self.compress = compress
    
    def get_db_path(self) -> str:
        """获取数据库文件路径"""
        return os.path.join(self.path, self.name, self.db_name)


class DiskQueue(BackpressureableQueueMixin, IQueue):
    """
    磁盘持久化优先队列
    
    特点：
    - 基于 SQLite 数据库存储
    - 支持优先级队列
    - 支持数据持久化
    - 支持断电恢复
    - 支持批量操作
    - 支持 TTL 自动清理
    - 支持数据压缩
    
    使用示例：
        config = DiskQueueConfig(path="/tmp/queue", max_size=10000)
        queue = DiskQueue(config)
        await queue.open()
        await queue.put(request, priority=5)
        request = await queue.get()
        await queue.close()
    """
    
    def __init__(self, config: DiskQueueConfig):
        """
        初始化磁盘队列
        
        Args:
            config: 磁盘队列配置
        """
        super().__init__(max_size=config.max_size, name=config.name)
        
        self._config = config
        self._db_path = config.get_db_path()
        self._connection_pool: List[sqlite3.Connection] = []
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._closed = False
        
        # 统计信息
        self._total_puts = 0
        self._total_gets = 0
        self._total_errors = 0
    
    async def open(self) -> None:
        """
        打开队列
        
        初始化数据库连接和表结构。
        """
        if self._closed:
            return
        
        # 创建目录
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        
        # 初始化连接池
        await self._init_connection_pool()
        
        # 创建表
        await self._create_table()
        
        # 启动清理任务
        if self._config.ttl > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self._stats.mark_start()
        logger.info(f"DiskQueue '{self._name}' opened at {self._db_path}")
    
    async def _init_connection_pool(self) -> None:
        """初始化连接池"""
        # 创建主连接用于写入
        conn = self._create_connection()
        conn.execute("PRAGMA journal_mode=WAL" if self._config.WAL_mode else "")
        conn.execute(f"PRAGMA cache_size=-{self._config.cache_size}")
        conn.execute(f"PRAGMA synchronous={self._config.synchronous}")
        self._connection_pool.append(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接"""
        conn = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            isolation_level="DEFERRED",
        )
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = self._create_connection()
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def _create_table(self) -> None:
        """创建队列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._config.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    priority INTEGER DEFAULT 0,
                    data BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    metadata TEXT,
                    processed INTEGER DEFAULT 0
                )
            """)
            
            # 创建索引
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_priority_created
                ON {self._config.table_name} (priority DESC, created_at ASC)
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON {self._config.table_name} (created_at)
            """)
            
            conn.commit()
    
    def _serialize(self, item: Any) -> bytes:
        """序列化数据"""
        try:
            if self._config.serialization == "json":
                data = json.dumps(item)
                return data.encode('utf-8')
            else:
                return pickle.dumps(item)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            raise
    
    def _deserialize(self, data: bytes) -> Any:
        """反序列化数据"""
        try:
            if self._config.serialization == "json":
                return json.loads(data.decode('utf-8'))
            else:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None
    
    async def put(self, item: Any, priority: int = 0) -> bool:
        """
        入队操作
        
        Args:
            item: 要入队的元素
            priority: 优先级，数值越小优先级越高（与框架统一）
            
        Returns:
            bool: 入队是否成功
        """
        if self._closed:
            logger.warning(f"Attempt to put item to closed queue '{self._name}'")
            self._stats.record_reject()
            return False
        
        # 检查队列大小限制
        if self._max_size > 0:
            current_size = await self.size()
            if current_size >= self._max_size:
                logger.warning(
                    f"Queue '{self._name}' is full ({current_size}/{self._max_size})"
                )
                self._stats.record_reject()
                return False
        
        # 应用背压控制
        if self._backpressure_enabled:
            should_backpressure = await self.should_apply_backpressure()
            if should_backpressure:
                delay = await self.calculate_backpressure_delay()
                if delay > 0:
                    await asyncio.sleep(delay)
        
        try:
            serialized = self._serialize(item)
            created_at = time.time()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    INSERT INTO {self._config.table_name}
                    (priority, data, created_at, processed)
                    VALUES (?, ?, ?, 0)
                    """,
                    (priority, serialized, created_at)
                )
                conn.commit()
            
            self._total_puts += 1
            self._stats.record_enqueue()
            self._stats.update_max_size(await self.size())
            
            return True
            
        except Exception as e:
            logger.error(f"Error putting item to queue '{self._name}': {e}")
            self._total_errors += 1
            self._stats.record_reject()
            return False
    
    async def put_batch(self, items: List[Any], default_priority: int = 0) -> int:
        """
        批量入队
        
        Args:
            items: 要入队的元素列表
            default_priority: 默认优先级
            
        Returns:
            int: 成功入队的数量
        """
        if not items:
            return 0
        
        success_count = 0
        created_at = time.time()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                data_batch = [
                    (default_priority, self._serialize(item), created_at)
                    for item in items
                ]
                
                cursor.executemany(
                    f"""
                    INSERT INTO {self._config.table_name}
                    (priority, data, created_at, processed)
                    VALUES (?, ?, ?, 0)
                    """,
                    data_batch
                )
                conn.commit()
            
            success_count = len(items)
            self._total_puts += success_count
            
            for _ in range(success_count):
                self._stats.record_enqueue()
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error in batch put to queue '{self._name}': {e}")
            self._total_errors += 1
            return 0
    
    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        出队操作
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            出队的元素，如果超时返回 None
        """
        if self._closed and await self.empty():
            return None
        
        timeout_value = timeout if timeout is not None else 0
        deadline = time.time() + timeout_value if timeout_value > 0 else None
        
        while True:
            if deadline and time.time() >= deadline:
                return None
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 获取最高优先级的未处理项（数值越小越优先）
                    cursor.execute(
                        f"""
                        SELECT id, priority, data, created_at
                        FROM {self._config.table_name}
                        WHERE processed = 0
                        ORDER BY priority ASC, created_at ASC
                        LIMIT 1
                        """
                    )
                    row = cursor.fetchone()
                    
                    if row is None:
                        if timeout_value == 0:
                            return None
                        await asyncio.sleep(0.1)
                        continue
                    
                    # 标记为已处理
                    cursor.execute(
                        f"""
                        UPDATE {self._config.table_name}
                        SET processed = 1
                        WHERE id = ?
                        """,
                        (row['id'],)
                    )
                    conn.commit()
                
                item = self._deserialize(row['data'])
                self._total_gets += 1
                self._stats.record_dequeue()
                return item
                
            except Exception as e:
                logger.error(f"Error getting item from queue '{self._name}': {e}")
                self._total_errors += 1
                return None
    
    async def get_batch(self, batch_size: int, timeout: Optional[float] = 1.0) -> List[Any]:
        """
        批量出队
        
        Args:
            batch_size: 最大批量大小
            timeout: 获取超时时间
            
        Returns:
            List: 出队的元素列表
        """
        items = []
        deadline = time.time() + timeout if timeout else None
        
        for _ in range(batch_size):
            if deadline and time.time() >= deadline:
                break
            
            item = await self.get(timeout=0.1)
            if item is None:
                break
            items.append(item)
        
        return items
    
    async def size(self) -> int:
        """
        获取队列大小
        
        Returns:
            int: 当前队列中的未处理元素数量
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT COUNT(*) as count
                    FROM {self._config.table_name}
                    WHERE processed = 0
                    """
                )
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
    
    async def total_size(self) -> int:
        """
        获取队列总大小（包括已处理的项）
        
        Returns:
            int: 总元素数量
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT COUNT(*) as count FROM {self._config.table_name}"
                )
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception:
            return 0
    
    async def empty(self) -> bool:
        """
        检查队列是否为空
        
        Returns:
            bool: 队列是否为空
        """
        return await self.size() == 0
    
    async def close(self) -> None:
        """
        关闭队列
        """
        self._closed = True
        
        # 停止清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 关闭连接
        for conn in self._connection_pool:
            try:
                conn.close()
            except Exception:
                pass
        
        self._stats.mark_end()
        
        logger.info(
            f"DiskQueue '{self._name}' closed. "
            f"Total puts: {self._total_puts}, gets: {self._total_gets}, "
            f"errors: {self._total_errors}"
        )
    
    async def clear(self) -> None:
        """清空队列"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self._config.table_name}")
                conn.commit()
            logger.debug(f"DiskQueue '{self._name}' cleared")
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
    
    async def _cleanup_loop(self) -> None:
        """定期清理过期数据"""
        while not self._closed:
            try:
                await asyncio.sleep(self._config.cleanup_interval)
                if self._closed:
                    break
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired(self) -> int:
        """
        清理过期数据
        
        Returns:
            int: 清理的项数量
        """
        if self._config.ttl <= 0:
            return 0
        
        try:
            deadline = time.time() - self._config.ttl
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    DELETE FROM {self._config.table_name}
                    WHERE created_at < ? AND processed = 1
                    """,
                    (deadline,)
                )
                deleted = cursor.rowcount
                conn.commit()
            
            if deleted > 0:
                logger.debug(f"Cleaned up {deleted} expired items from queue '{self._name}'")
            
            # 执行 VACUUM 回收空间
            if deleted > 1000:
                with self._get_connection() as conn:
                    conn.execute("VACUUM")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up expired items: {e}")
            return 0
    
    def get_extended_stats(self) -> Dict[str, Any]:
        """
        获取扩展统计信息
        
        Returns:
            Dict: 扩展统计信息
        """
        try:
            total_items = 0
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) as count FROM {self._config.table_name}")
                row = cursor.fetchone()
                total_items = row['count'] if row else 0
        except Exception:
            total_items = -1
        
        return {
            'queue_type': QueueType.DISK.value,
            'name': self._name,
            'db_path': self._db_path,
            'max_size': self._max_size,
            'total_puts': self._total_puts,
            'total_gets': self._total_gets,
            'total_errors': self._total_errors,
            'total_items': total_items,
            'config': {
                'ttl': self._config.ttl,
                'serialization': self._config.serialization,
                'compress': self._config.compress,
            },
            'base_stats': self._stats.to_dict(),
        }
    
    def __del__(self):
        """析构函数，确保关闭连接"""
        for conn in self._connection_pool:
            try:
                conn.close()
            except Exception:
                pass


__all__ = [
    'DiskQueue',
    'DiskQueueConfig',
]
