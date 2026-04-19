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
3. 资源安全：自动管理连接池生命周期
4. 协程集成：与框架异步协程无缝配合

使用示例：
```python
from crawlo.tools.mysql_exists_checker import MySQLExistsChecker

# 在 Spider 中使用
class MySpider(Spider):
    name = 'my_spider'
    
    async def parse_list(self, response):
        for item in response.json():
            # 检查数据是否已存在
            sql = f"SELECT 1 FROM articles WHERE url = '{item['url']}' LIMIT 1"
            checker = MySQLExistsChecker(self.settings)
            exists = await checker.exists(sql)
            
            if not exists:
                # 数据不存在，解析详情页
                yield Request(item['detail_url'], callback=self.parse_detail)
    
    async def parse_detail(self, response):
        # 解析详情页数据
        yield {'url': response.url, 'title': response.css('title::text').get()}
```

Author: Crawlo Team
Version: 0.2.0
"""

import asyncio
from typing import Optional, Any
from crawlo.logging import get_logger

# 导入连接池管理器
try:
    from crawlo.utils.db.mysql_connection_pool import MySQLConnectionPoolManager
    POOL_MANAGER_AVAILABLE = True
except ImportError:
    POOL_MANAGER_AVAILABLE = False
    MySQLConnectionPoolManager = None


class MySQLExistsChecker:
    """
    MySQL 数据存在性检查器
    
    用于快速检查数据库中是否存在满足条件的记录。
    专门优化用于爬虫列表页去重场景，避免不必要的详情页请求。
    
    使用方法：
    ```python
    # 方式1：在 Spider 生命周期内使用（推荐）
    checker = MySQLExistsChecker(crawler.settings)
    
    # 检查数据是否存在
    exists = await checker.exists("SELECT 1 FROM articles WHERE url = %s LIMIT 1", ("https://...",))
    
    # 关闭连接池（通常在 Spider 关闭时调用）
    await checker.close()
    
    # 方式2：使用上下文管理器（自动管理资源）
    async with MySQLExistsChecker(crawler.settings) as checker:
        exists = await checker.exists("SELECT 1 FROM articles WHERE id = %s", (123,))
    ```
    
    Attributes:
        settings: Crawlo 配置对象
        logger: 日志记录器
    """
    
    def __init__(self, settings: Optional[Any] = None):
        """
        初始化存在性检查器
        
        Args:
            settings: Crawlo 配置对象（支持 Settings 类或 dict）
                      如果为 None，将尝试使用默认配置
        """
        self.settings = settings
        self.logger = get_logger(f'MySQLExistsChecker.{id(self)}')
        self._pool = None
        self._pool_key = f'exists_checker_{id(self)}'
        self._closed = False
        self._lock = asyncio.Lock()
        
        # 从 settings 提取数据库配置
        self._db_config = self._extract_db_config()
    
    def _extract_db_config(self) -> dict:
        """
        从 settings 提取数据库配置
        
        Returns:
            dict: 数据库连接配置
        """
        if self.settings is None:
            return {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'db': 'crawlo',
                'minsize': 2,
                'maxsize': 5,
            }
        
        # 支持 Settings 对象或 dict
        get = getattr(self.settings, 'get', None)
        get_int = getattr(self.settings, 'get_int', None)
        
        if get and get_int:
            # Settings 对象
            return {
                'host': get('MYSQL_HOST', 'localhost'),
                'port': get_int('MYSQL_PORT', 3306),
                'user': get('MYSQL_USER', 'root'),
                'password': get('MYSQL_PASSWORD', ''),
                'db': get('MYSQL_DB', 'crawlo'),
                'minsize': get_int('MYSQL_POOL_MIN', 2),
                'maxsize': get_int('MYSQL_POOL_MAX', 5),
            }
        elif isinstance(self.settings, dict):
            # dict 对象
            return {
                'host': self.settings.get('MYSQL_HOST', 'localhost'),
                'port': self.settings.get('MYSQL_PORT', 3306),
                'user': self.settings.get('MYSQL_USER', 'root'),
                'password': self.settings.get('MYSQL_PASSWORD', ''),
                'db': self.settings.get('MYSQL_DB', 'crawlo'),
                'minsize': self.settings.get('MYSQL_POOL_MIN', 2),
                'maxsize': self.settings.get('MYSQL_POOL_MAX', 5),
            }
        else:
            # 默认配置
            return {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'db': 'crawlo',
                'minsize': 2,
                'maxsize': 5,
            }
    
    async def _get_pool(self):
        """
        获取或创建连接池（懒加载）
        
        Returns:
            连接池实例
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，无法获取连接池")
        
        if self._pool is None:
            async with self._lock:
                # 双重检查
                if self._pool is None:
                    if not POOL_MANAGER_AVAILABLE:
                        raise RuntimeError(
                            "MySQL 连接池不可用，请确保已安装 asyncmy 或 aiomysql"
                        )
                    
                    self._pool = await MySQLConnectionPoolManager.get_pool(
                        host=self._db_config['host'],
                        port=self._db_config['port'],
                        user=self._db_config['user'],
                        password=self._db_config['password'],
                        db=self._db_config['db'],
                        minsize=self._db_config['minsize'],
                        maxsize=self._db_config['maxsize'],
                        shared=True,  # 共享连接池，复用框架连接
                    )
                    self.logger.debug(
                        f"连接池已创建: {self._db_config['host']}:{self._db_config['port']}"
                    )
        
        return self._pool
    
    async def exists(self, sql: str, params: tuple = None) -> bool:
        """
        检查数据是否存在
        
        执行指定的 SQL 查询（通常使用 LIMIT 1），返回是否存在记录。
        
        Args:
            sql: SQL 查询语句，必须使用 LIMIT 1 限制返回行数
                 示例: "SELECT 1 FROM articles WHERE url = %s LIMIT 1"
            params: SQL 参数元组（可选）
                    示例: ("https://example.com/article/123",)
        
        Returns:
            bool: 如果查询返回至少一行记录则返回 True，否则返回 False
        
        Raises:
            RuntimeError: 如果检查器已关闭
            Exception: 数据库执行错误
        
        Example:
            ```python
            # 基本用法
            checker = MySQLExistsChecker(settings)
            exists = await checker.exists(
                "SELECT 1 FROM articles WHERE url = %s LIMIT 1",
                ("https://example.com/article/1",)
            )
            
            # 多条件查询
            exists = await checker.exists(
                "SELECT 1 FROM articles WHERE title = %s AND date = %s LIMIT 1",
                ("标题", "2024-01-01")
            )
            
            # 使用格式化字符串（注意 SQL 注入风险，建议使用参数）
            exists = await checker.exists(
                f"SELECT 1 FROM articles WHERE url = 'https://example.com' LIMIT 1"
            )
            ```
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 执行查询
                    if params:
                        await cursor.execute(sql, params)
                    else:
                        await cursor.execute(sql)
                    
                    # 获取结果
                    result = await cursor.fetchone()
                    
                    # 返回是否存在
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
                 示例: "SELECT url FROM articles WHERE url IN ({}) LIMIT 1"
            params_list: 参数列表
                         示例: [("url1",), ("url2",), ("url3",)]
        
        Returns:
            list: 每个参数对应的存在性结果列表
                  示例: [True, False, True]  # 第一个和第三个存在
        
        Example:
            ```python
            checker = MySQLExistsChecker(settings)
            urls = ["url1", "url2", "url3"]
            placeholders = ", ".join(["%s"] * len(urls))
            sql = f"SELECT url FROM articles WHERE url IN ({placeholders})"
            
            # 获取已存在的 URL
            params_list = [(url,) for url in urls]
            exists_list = await checker.batch_exists(sql, params_list)
            
            for url, exists in zip(urls, exists_list):
                if not exists:
                    yield Request(url, callback=self.parse_detail)
            ```
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 合并所有参数
                    all_params = []
                    for params in params_list:
                        all_params.extend(params)
                    
                    # 执行查询
                    await cursor.execute(sql, all_params)
                    results = await cursor.fetchall()
                    
                    # 获取存在的值
                    existing = {r[0] for r in results}
                    
                    # 返回每个参数的存在性
                    return [params[0] in existing for params in params_list]
                    
        except Exception as e:
            self.logger.error(f"批量存在性检查失败: {e}")
            raise
    
    async def count(self, sql: str, params: tuple = None) -> int:
        """
        统计满足条件的记录数
        
        Args:
            sql: SQL 查询语句
                 示例: "SELECT COUNT(*) FROM articles WHERE status = %s"
            params: SQL 参数元组（可选）
        
        Returns:
            int: 记录数量
        
        Example:
            ```python
            checker = MySQLExistsChecker(settings)
            count = await checker.count(
                "SELECT COUNT(*) FROM articles WHERE date = %s",
                ("2024-01-01",)
            )
            print(f"今日共采集 {count} 条数据")
            ```
        """
        if self._closed:
            raise RuntimeError("MySQLExistsChecker 已关闭，请重新创建实例")
        
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
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
        关闭检查器并释放资源
        
        注意：由于使用共享连接池，此方法不会真正关闭连接池，
        只是清理当前实例的引用。连接池由 MySQLConnectionPoolManager
        统一管理。
        
        调用此方法后，检查器将无法继续使用。
        """
        if self._closed:
            return
        
        self._closed = True
        self._pool = None
        self.logger.debug("MySQLExistsChecker 资源已清理")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口，自动关闭"""
        await self.close()
        return False
    
    def __del__(self):
        """析构函数，确保资源清理"""
        if not self._closed and self._pool:
            # 尝试创建异步任务关闭（如果在事件循环中）
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.close())
            except Exception:
                pass
    
    def is_closed(self) -> bool:
        """
        检查检查器是否已关闭
        
        Returns:
            bool: 是否已关闭
        """
        return self._closed


# 便捷函数
async def check_exists(
    sql: str, 
    params: tuple = None,
    settings: Optional[Any] = None
) -> bool:
    """
    快速检查数据是否存在（便捷函数）
    
    适用于一次性检查场景，自动管理资源。
    
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
    async with MySQLExistsChecker(settings) as checker:
        return await checker.exists(sql, params)


# 导出
__all__ = [
    'MySQLExistsChecker',
    'check_exists',
]
