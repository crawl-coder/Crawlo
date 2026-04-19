#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQL 数据存在性检查工具
========================

Crawlo 框架的 MySQL 数据存在性检查工具，用于在爬虫列表页采集时，
提前判断数据是否已存在于数据库中，避免不必要的详情页解析请求。

使用场景：
- 采集列表页时，检查数据是否已存在
- 避免重复请求已采集的数据
- 节省网络资源和解析资源

特点：
1. 简单易用：只需传入 SQL 语句即可判断存在性
2. 自动配置：自动从 settings 获取数据库连接信息
3. 连接池复用：使用单例模式，避免频繁创建/销毁连接
4. 协程集成：与框架异步协程无缝配合
5. 生命周期管理：爬虫结束时统一关闭连接池

使用示例：
```python
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker

# 在 Spider 中使用（连接池在整个爬虫生命周期内复用）
class MySpider(Spider):
    name = 'my_spider'
    
    async def start_requests(self):
        # 创建检查器（在爬虫开始时）
        self.db_checker = MySQLExistsChecker.from_settings(self.settings)
        yield from self._get_initial_requests()
    
    async def parse_list(self, response):
        for item in response.json():
            # 检查数据是否已存在（复用连接池）
            sql = "SELECT 1 FROM articles WHERE url = %s LIMIT 1"
            exists = await self.db_checker.exists(sql, (item['url'],))
            
            if not exists:
                yield Request(item['detail_url'], callback=self.parse_detail)
    
    async def closed(self):
        # 爬虫结束时统一关闭（重要！）
        await self.db_checker.close()
```

Author: Crawlo Team
Version: 0.2.0
"""

import asyncio
from typing import Optional, Any, Dict
from crawlo.logging import get_logger

# MySQL 驱动导入（同时支持 asyncmy 和 aiomysql）
try:
    from asyncmy import create_pool as asyncmy_create_pool
    ASYNCMY_AVAILABLE = True
except ImportError:
    asyncmy_create_pool = None
    ASYNCMY_AVAILABLE = False

try:
    import aiomysql
    AIOMYSQL_AVAILABLE = True
except ImportError:
    aiomysql = None
    AIOMYSQL_AVAILABLE = False


# ============================================================
# 单例连接池管理器（模块级）
# ============================================================

class _MySQLPoolManager:
    """
    MySQL 连接池单例管理器
    
    确保整个爬虫生命周期内只有一个连接池实例，
    避免频繁创建/销毁连接带来的性能开销。
    
    Attributes:
        _pools: Dict[str, pool] - 按配置哈希存储的连接池
        _lock: asyncio.Lock - 创建连接池时的锁
    """
    
    _pools: Dict[str, Any] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_pool(cls, config: Dict[str, Any]) -> Any:
        """
        获取或创建连接池（单例模式）
        
        Args:
            config: 数据库配置字典
            
        Returns:
            连接池实例
        """
        # 生成配置哈希作为 key
        pool_key = cls._generate_key(config)
        
        # 检查是否已存在
        if pool_key in cls._pools:
            return cls._pools[pool_key]
        
        # 创建新的连接池
        async with cls._lock:
            # 双重检查
            if pool_key in cls._pools:
                return cls._pools[pool_key]
            
            pool = await cls._create_pool(config)
            cls._pools[pool_key] = pool
            return pool
    
    @classmethod
    def _generate_key(cls, config: Dict[str, Any]) -> str:
        """生成配置哈希"""
        return f"{config['host']}:{config['port']}/{config['db']}"
    
    @classmethod
    async def _create_pool(cls, config: Dict[str, Any]) -> Any:
        """创建连接池"""
        pool_config = {
            'host': config['host'],
            'port': config['port'],
            'user': config['user'],
            'password': config['password'],
            'db': config['db'],
            'minsize': config.get('minsize', 2),
            'maxsize': config.get('maxsize', 5),
        }
        
        logger = get_logger('MySQLExistsChecker.Pool')
        
        # 优先使用 asyncmy（性能更好），其次 aiomysql
        if ASYNCMY_AVAILABLE:
            pool = await asyncmy_create_pool(**pool_config)
            logger.debug(f"asyncmy 连接池已创建: {pool_config['host']}:{pool_config['port']}")
        elif AIOMYSQL_AVAILABLE:
            pool = await aiomysql.create_pool(**pool_config)
            logger.debug(f"aiomysql 连接池已创建: {pool_config['host']}:{pool_config['port']}")
        else:
            raise RuntimeError(
                f"MySQL 连接池不可用，请安装 asyncmy 或 aiomysql\n"
                f"安装命令: pip install asyncmy 或 pip install aiomysql"
            )
        
        return pool
    
    @classmethod
    async def close_all(cls):
        """关闭所有连接池（爬虫结束时调用）"""
        async with cls._lock:
            for key, pool in list(cls._pools.items()):
                try:
                    pool.close()
                    await pool.wait_closed()
                    get_logger('MySQLExistsChecker.Pool').debug(f"连接池已关闭: {key}")
                except Exception as e:
                    get_logger('MySQLExistsChecker.Pool').warning(f"关闭连接池失败: {key}, {e}")
            cls._pools.clear()
    
    @classmethod
    def get_pool_count(cls) -> int:
        """获取当前连接池数量"""
        return len(cls._pools)


# ============================================================
# MySQLExistsChecker
# ============================================================

class MySQLExistsChecker:
    """
    MySQL 数据存在性检查器
    
    用于快速检查数据库中是否存在满足条件的记录。
    专门优化用于爬虫列表页去重场景，避免不必要的详情页请求。
    
    使用方法：
    ```python
    # 在 Spider 中使用
    class MySpider(Spider):
        async def start_requests(self):
            self.db_checker = MySQLExistsChecker.from_settings(self.settings)
            # ...
        
        async def parse_list(self, response):
            exists = await self.db_checker.exists(sql, (url,))
            if not exists:
                yield Request(url, callback=self.parse_detail)
        
        async def closed(self):
            await self.db_checker.close()
    ```
    
    Attributes:
        _config: 数据库配置
        _pool: 连接池引用（不持有所有权）
        logger: 日志记录器
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化检查器
        
        Args:
            config: 数据库配置字典
                   {
                       'host': 'localhost',
                       'port': 3306,
                       'user': 'root',
                       'password': '',
                       'db': 'crawlo',
                       'minsize': 2,
                       'maxsize': 5,
                   }
        """
        self._config = config
        self._pool = None
        self.logger = get_logger(f'MySQLExistsChecker')
        self._closed = False
        self._lock = asyncio.Lock()
    
    @classmethod
    def from_settings(cls, settings: Any) -> 'MySQLExistsChecker':
        """
        从 Crawlo settings 创建检查器（推荐方式）
        
        Args:
            settings: Crawlo 配置对象（支持 Settings 类或 dict）
        
        Returns:
            MySQLExistsChecker 实例
        """
        # 提取配置
        if settings is None:
            config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'db': 'crawlo',
                'minsize': 2,
                'maxsize': 5,
            }
        elif isinstance(settings, dict):
            config = {
                'host': settings.get('MYSQL_HOST', 'localhost'),
                'port': settings.get('MYSQL_PORT', 3306),
                'user': settings.get('MYSQL_USER', 'root'),
                'password': settings.get('MYSQL_PASSWORD', ''),
                'db': settings.get('MYSQL_DB', 'crawlo'),
                'minsize': settings.get('MYSQL_POOL_MIN', 2),
                'maxsize': settings.get('MYSQL_POOL_MAX', 5),
            }
        else:
            # Settings 对象
            config = {
                'host': settings.get('MYSQL_HOST', 'localhost'),
                'port': settings.get_int('MYSQL_PORT', 3306),
                'user': settings.get('MYSQL_USER', 'root'),
                'password': settings.get('MYSQL_PASSWORD', ''),
                'db': settings.get('MYSQL_DB', 'crawlo'),
                'minsize': settings.get_int('MYSQL_POOL_MIN', 2),
                'maxsize': settings.get_int('MYSQL_POOL_MAX', 5),
            }
        
        return cls(config)
    
    async def _get_pool(self):
        """
        获取连接池（懒加载，单例模式）
        
        Returns:
            连接池实例
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    self._pool = await _MySQLPoolManager.get_pool(self._config)
        
        return self._pool
    
    async def exists(self, sql: str, params: tuple = None) -> bool:
        """
        检查数据是否存在
        
        Args:
            sql: SQL 查询语句，必须使用 LIMIT 1 限制返回行数
                 示例: "SELECT 1 FROM articles WHERE url = %s LIMIT 1"
            params: SQL 参数元组（可选）
                    示例: ("https://example.com/article/123",)
        
        Returns:
            bool: 如果查询返回至少一行记录则返回 True，否则返回 False
        
        Raises:
            RuntimeError: 如果检查器已关闭
        
        Example:
            ```python
            checker = MySQLExistsChecker.from_settings(settings)
            exists = await checker.exists(
                "SELECT 1 FROM articles WHERE url = %s LIMIT 1",
                ("https://example.com/article/1",)
            )
            ```
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    if params:
                        await cursor.execute(sql, params)
                    else:
                        await cursor.execute(sql)
                    
                    result = await cursor.fetchone()
                    return result is not None
                except Exception as e:
                    self.logger.error(f"执行存在性检查失败: {e}, SQL: {sql[:100]}...")
                    raise
    
    async def batch_exists(
        self, 
        sql: str, 
        params_list: list
    ) -> list:
        """
        批量检查数据是否存在
        
        对于批量 URL 检查场景，使用 IN 查询优化性能。
        
        Args:
            sql: SQL 查询语句，必须使用 IN 占位符
                 示例: "SELECT url FROM articles WHERE url IN ({})"
            params_list: 参数列表
                         示例: [("url1",), ("url2",), ("url3",)]
        
        Returns:
            list: 每个参数对应的存在性结果列表
                  示例: [True, False, True]  # 第一个和第三个存在
        
        Example:
            ```python
            checker = MySQLExistsChecker.from_settings(settings)
            urls = ["url1", "url2", "url3"]
            placeholders = ", ".join(["%s"] * len(urls))
            sql = f"SELECT url FROM articles WHERE url IN ({placeholders})"
            
            params_list = [(url,) for url in urls]
            exists_list = await checker.batch_exists(sql, params_list)
            
            for url, exists in zip(urls, exists_list):
                if not exists:
                    yield Request(url, callback=self.parse_detail)
            ```
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # 合并所有参数
                    all_params = []
                    for params in params_list:
                        all_params.extend(params)
                    
                    await cursor.execute(sql, all_params)
                    results = await cursor.fetchall()
                    
                    existing = {r[0] for r in results}
                    return [params[0] in existing for params in params_list]
                except Exception as e:
                    self.logger.error(f"批量存在性检查失败: {e}")
                    raise
    
    async def count(self, sql: str, params: tuple = None) -> int:
        """
        统计满足条件的记录数
        
        Args:
            sql: SQL 查询语句
                 示例: "SELECT COUNT(*) FROM articles WHERE date = %s"
            params: SQL 参数元组（可选）
        
        Returns:
            int: 记录数量
        
        Example:
            ```python
            checker = MySQLExistsChecker.from_settings(settings)
            count = await checker.count(
                "SELECT COUNT(*) FROM articles WHERE date = %s",
                ("2024-01-01",)
            )
            print(f"今日共采集 {count} 条数据")
            ```
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    if params:
                        await cursor.execute(sql, params)
                    else:
                        await cursor.execute(sql)
                    
                    result = await cursor.fetchone()
                    return result[0] if result else 0
                except Exception as e:
                    self.logger.error(f"统计查询失败: {e}")
                    raise
    
    async def close(self):
        """
        关闭检查器
        
        注意：此方法只标记检查器为已关闭，
        实际连接池由 _MySQLPoolManager 统一管理，
        不会在这里关闭。连接池的关闭应该在爬虫结束时
        调用 MySQLExistsChecker.close_all() 统一关闭。
        
        这样设计的好处：
        1. 多个检查器可以共享同一个连接池
        2. 避免重复创建/销毁连接
        3. 爬虫结束时统一关闭所有连接池
        """
        if self._closed:
            return
        
        self._closed = True
        self._pool = None  # 只是断开引用，不关闭连接池
        self.logger.debug("MySQLExistsChecker 已标记为关闭")
    
    async def close_all():
        """
        关闭所有连接池（类方法）
        
        在爬虫结束时调用，关闭所有由 MySQLExistsChecker 创建的连接池。
        
        Example:
            ```python
            class MySpider(Spider):
                async def closed(self):
                    await MySQLExistsChecker.close_all()
            ```
        """
        await _MySQLPoolManager.close_all()
    
    @staticmethod
    def get_pool_count() -> int:
        """获取当前连接池数量"""
        return _MySQLPoolManager.get_pool_count()
    
    def is_closed(self) -> bool:
        """检查检查器是否已关闭"""
        return self._closed


# 便捷函数
async def check_exists(
    sql: str, 
    params: tuple = None,
    settings: Any = None
) -> bool:
    """
    快速检查数据是否存在（便捷函数）
    
    适用于一次性检查场景。建议在批量操作时使用 MySQLExistsChecker 类。
    
    Args:
        sql: SQL 查询语句
        params: SQL 参数元组（可选）
        settings: Crawlo 配置对象（可选）
    
    Returns:
        bool: 是否存在
    
    Example:
        ```python
        # 一次性检查
        exists = await check_exists(
            "SELECT 1 FROM articles WHERE url = %s LIMIT 1",
            ("https://example.com",),
            crawler.settings
        )
        ```
    """
    checker = MySQLExistsChecker.from_settings(settings)
    try:
        return await checker.exists(sql, params)
    finally:
        await checker.close()


# 导出
__all__ = [
    'MySQLExistsChecker',
    'check_exists',
]
