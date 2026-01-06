# -*- coding: utf-8 -*-
import re
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

import async_timeout

from . import BasePipeline
from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.db_helper import SQLBuilder
from crawlo.utils.database_connection_pool import DatabaseConnectionPoolManager


class BaseMySQLPipeline(BasePipeline, ABC):
    """MySQL管道的基类，封装公共功能"""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)

        # 记录管道初始化
        self.logger.info(f"MySQL管道初始化完成: {self.__class__.__name__}")

        # 使用异步锁和初始化标志确保线程安全
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        
        # 优先从爬虫的custom_settings中获取表名，如果没有则使用默认值
        spider_table_name = None
        if hasattr(crawler, 'spider') and crawler.spider and hasattr(crawler.spider, 'custom_settings'):
            spider_table_name = crawler.spider.custom_settings.get('MYSQL_TABLE')
            
        self.table_name = (
                spider_table_name or
                self.settings.get('MYSQL_TABLE') or
                getattr(crawler.spider, 'mysql_table', None) or
                f"{getattr(crawler.spider, 'name', 'default')}_items"
        )
        
        # 验证表名是否有效
        if not self.table_name or not isinstance(self.table_name, str):
            raise ValueError(f"Invalid table name: {self.table_name}. Table name must be a non-empty string.")
        
        # 清理表名，移除可能的非法字符
        self.table_name = self.table_name.strip().replace(' ', '_').replace('-', '_')
        
        # 使用正则只允许安全字符
        if not re.match(r'^[a-zA-Z0-9_]+$', self.table_name):
             raise ValueError(f"Table name contains illegal characters: {self.table_name}")
        
        # 批量插入配置
        self.batch_size = max(1, self.settings.get_int('MYSQL_BATCH_SIZE', 100))  # 确保至少为1
        self.use_batch = self.settings.get_bool('MYSQL_USE_BATCH', False)
        self.batch_buffer: List[Dict] = []  # 批量缓冲区

        # SQL生成配置
        self.auto_update = self.settings.get_bool('MYSQL_AUTO_UPDATE', False)
        self.insert_ignore = self.settings.get_bool('MYSQL_INSERT_IGNORE', False)
        self.update_columns = self.settings.get('MYSQL_UPDATE_COLUMNS', ())
        
        # 验证 update_columns 是否为元组或列表
        if self.update_columns and not isinstance(self.update_columns, (tuple, list)):
            self.logger.warning(f"更新列配置应该是一个元组或列表，当前类型为 {type(self.update_columns)}。已自动转换为元组。")
            self.update_columns = (self.update_columns,)

        # 注册关闭事件
        crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')

    async def process_item(self, item: Item, spider, **kwargs) -> Item:
        """处理item的核心方法"""
        spider_name = getattr(spider, 'name', 'unknown')  # 获取爬虫名称
        
        # 如果启用批量插入，将item添加到缓冲区
        if self.use_batch:
            # 在锁的保护下添加到缓冲区，确保线程安全
            async with self._pool_lock:
                self.batch_buffer.append(dict(item))
                
                # 如果缓冲区达到批量大小，执行批量插入
                should_flush = len(self.batch_buffer) >= self.batch_size
            
            if should_flush:
                try:
                    await self._flush_batch(spider_name)
                except Exception as e:
                    # 即使批量刷新失败，也要确保item被返回，避免爬虫中断
                    self.logger.error(f"批量刷新失败，但继续处理: {e}")
                    # 这里不重新抛出异常，让爬虫可以继续运行
            
            return item
        else:
            # 单条插入逻辑
            try:
                await self._ensure_pool()
                
                # 检查连接池是否有效
                if not self._pool_initialized or not self.pool:
                    raise RuntimeError("Database connection pool is not initialized or invalid")
                
                item_dict = dict(item)
                sql, params = await self._make_insert_sql(item_dict, prefer_alias=True, **kwargs)
                try:
                    rowcount = await self._execute_sql(sql=sql, values=params)
                except Exception as e:
                    err_str = str(e)
                    if self.update_columns and ("AS `excluded`" in sql) and ("You have an error in your SQL syntax" in err_str or "near 'AS" in err_str or "Unknown column 'excluded'" in err_str):
                        sql_fallback, params_fallback = await self._make_insert_sql(item_dict, prefer_alias=False, **kwargs)
                        rowcount = await self._execute_sql(sql=sql_fallback, values=params_fallback)
                    else:
                        raise
                if rowcount > 1:
                    self.logger.info(
                        f"爬虫 {spider_name} 成功插入 {rowcount} 条记录到表 {self.table_name}"
                    )
                elif rowcount == 1:
                    self.logger.debug(
                        f"爬虫 {spider_name} 成功插入单条记录到表 {self.table_name}"
                    )
                else:
                    # 当使用 MYSQL_UPDATE_COLUMNS 时，如果更新的字段值与现有记录相同，
                    # MySQL 不会实际更新任何数据，rowcount 会是 0
                    if self.update_columns:
                        self.logger.info(
                            f"爬虫 {spider_name}: 数据已存在，{self.update_columns}字段未发生变化，无需更新"
                        )
                    else:
                        self.logger.warning(
                            f"爬虫 {spider_name}: SQL执行成功但未插入新记录"
                        )

                # 统计计数移到这里，与AiomysqlMySQLPipeline保持一致
                self.crawler.stats.inc_value('mysql/insert_success')
                self.crawler.stats.inc_value('mysql/rows_requested', 1)
                self.crawler.stats.inc_value('mysql/rows_affected', rowcount or 0)
                if self.insert_ignore and not self.update_columns and (rowcount or 0) == 0:
                    self.crawler.stats.inc_value('mysql/rows_ignored_by_duplicate', 1)
                return item

            except Exception as e:
                # 添加更多调试信息
                error_msg = f"处理失败: {str(e)}"
                self.logger.error(f"处理数据项时发生错误: {error_msg}")
                self.crawler.stats.inc_value('mysql/insert_failed')
                raise ItemDiscard(error_msg)

    @abstractmethod
    async def _execute_sql(self, sql: str, values: Optional[list] = None) -> int:
        """执行SQL语句并处理结果 - 子类需要重写此方法"""
        raise NotImplementedError("子类必须实现 _execute_sql 方法")

    @abstractmethod
    async def _execute_batch_sql(self, sql: str, values_list: list) -> int:
        """执行批量SQL语句 - 子类需要重写此方法"""
        raise NotImplementedError("子类必须实现 _execute_batch_sql 方法")

    async def _flush_batch(self, spider_name: str):
        """刷新批量缓冲区并执行批量插入"""
        # 快照当前批量，避免在 await 过程中 buffer 被其他协程修改
        # 先在锁外获取当前批次数据，避免长时间持有锁
        async with self._pool_lock:
            if not self.batch_buffer:
                return
                
            # 使用切片复制，避免引用同一对象；不立即清空，失败时可重试
            current_batch = self.batch_buffer[:]
            processed_count = len(current_batch)
            # 立即清空缓冲区，避免重复处理
            self.batch_buffer.clear()
        
        if not current_batch:  # 双重检查
            return
        
        try:
            await self._ensure_pool()
            
            # 检查连接池是否有效
            if not self._pool_initialized or not self.pool:
                raise RuntimeError("Database connection pool is not initialized or invalid")
            
            # 使用 SQLBuilder 生成批量插入 SQL
            batch_result = SQLBuilder.make_batch(
                table=self.table_name,
                datas=current_batch,  # 使用局部变量
                auto_update=self.auto_update,
                update_columns=self.update_columns,
                prefer_alias=self.settings.get_bool('MYSQL_PREFER_ALIAS', True)
            )

            if batch_result:
                sql, values_list = batch_result
                try:
                    rowcount = await self._execute_batch_sql(sql=sql, values_list=values_list)
                except Exception as e:
                    err_str = str(e)
                    if self.update_columns and ("AS `excluded`" in sql) and ("You have an error in your SQL syntax" in err_str or "near 'AS" in err_str or "Unknown column 'excluded'" in err_str):
                        batch_result_fb = SQLBuilder.make_batch(
                            table=self.table_name,
                            datas=current_batch,
                            auto_update=self.auto_update,
                            update_columns=self.update_columns,
                            prefer_alias=not self.settings.get_bool('MYSQL_PREFER_ALIAS', True)
                        )
                        if batch_result_fb:
                            sql_fb, values_list_fb = batch_result_fb
                            rowcount = await self._execute_batch_sql(sql=sql_fb, values_list=values_list_fb)
                        else:
                            rowcount = 0
                    else:
                        raise
                
                if rowcount > 0:
                    self.logger.info(
                        f"爬虫 {spider_name} 批量插入 {processed_count} 条记录到表 {self.table_name}，实际影响 {rowcount} 行"
                    )
                else:
                    # 当使用 MYSQL_UPDATE_COLUMNS 时，如果更新的字段值与现有记录相同，
                    # MySQL 不会实际更新任何数据，rowcount 会是 0
                    if self.update_columns:
                        self.logger.info(
                            f"爬虫 {spider_name}: 批量数据已存在，{self.update_columns}字段未发生变化，无需更新"
                        )
                    else:
                        self.logger.warning(
                            f"爬虫 {spider_name}: 批量SQL执行完成但未插入新记录"
                        )

                self.crawler.stats.inc_value('mysql/batch_insert_success')
                self.crawler.stats.inc_value('mysql/rows_requested', processed_count)
                self.crawler.stats.inc_value('mysql/rows_affected', rowcount or 0)
                if self.insert_ignore and not self.update_columns and (rowcount or 0) < processed_count:
                    self.crawler.stats.inc_value('mysql/rows_ignored_by_duplicate', processed_count - (rowcount or 0))
            else:
                self.logger.warning(f"爬虫 {spider_name}: 批量数据为空，跳过插入")
                # 如果没有数据要处理，重新将数据放回缓冲区
                async with self._pool_lock:
                    self.batch_buffer.extend(current_batch)

        except Exception as e:
            # 添加更多调试信息
            error_msg = f"批量插入失败: {str(e)}"
            self.logger.error(f"批量处理数据时发生错误: {error_msg}")
            self.crawler.stats.inc_value('mysql/batch_insert_failed')
            # 失败时将数据重新放回缓冲区，以便重试
            async with self._pool_lock:
                self.batch_buffer.extend(current_batch)
            raise ItemDiscard(error_msg)

    async def spider_closed(self):
        """关闭爬虫时清理资源"""
        # 在关闭前强制刷新剩余的批量数据
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            try:
                await self._flush_batch(spider_name)
                # 再次检查是否还有剩余数据（可能由于异常处理等原因）
                if self.batch_buffer:
                    self.logger.warning(f"爬虫关闭时仍有 {len(self.batch_buffer)} 条数据未处理")
            except Exception as e:
                self.logger.error(f"关闭爬虫时刷新批量数据失败: {e}")
                # 即使刷新失败，也要记录未处理的数据量
                if self.batch_buffer:
                    self.logger.error(f"爬虫关闭时有 {len(self.batch_buffer)} 条数据未能插入数据库")
        
        # 注意：不再关闭连接池，因为连接池是全局共享的
        # 连接池的关闭由 DatabaseConnectionPoolManager.close_all_mysql_pools() 统一管理
        if self.pool:
            self.logger.info(
                f"MySQL Pipeline 关闭，但保留全局共享连接池以供其他爬虫使用"
            )
            
    async def _make_insert_sql(self, item_dict: Dict, **kwargs) -> Tuple[str, List[Any]]:
        """生成插入SQL语句，子类可以重写此方法"""
        # 合并管道配置和传入的kwargs参数
        # 优先使用传入的prefer_alias参数，否则从设置中获取默认值
        prefer_alias = kwargs.pop('prefer_alias', self.settings.get_bool('MYSQL_PREFER_ALIAS', True))
        sql_kwargs = {
            'auto_update': self.auto_update,
            'insert_ignore': self.insert_ignore,
            'update_columns': self.update_columns,
            'prefer_alias': prefer_alias
        }
        sql_kwargs.update(kwargs)
        
        return SQLBuilder.make_insert(
            table=self.table_name, 
            data=item_dict, 
            **sql_kwargs
        )
        
    @abstractmethod
    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全），子类必须实现此方法"""
        pass


class AsyncmyMySQLPipeline(BaseMySQLPipeline):
    """使用asyncmy库的MySQL管道实现"""
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger.info(f"创建AsyncmyMySQLPipeline实例，配置信息 - 主机: {self.settings.get('MYSQL_HOST', 'localhost')}, 数据库: {self.settings.get('MYSQL_DB', 'scrapy_db')}, 表名: {self.table_name}")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        if self._pool_initialized and self.pool:
            # 检查连接池是否仍然有效
            # 对于 asyncmy，使用 _closed 属性检查连接池状态
            if hasattr(self.pool, '_closed'):
                if not self.pool._closed:
                    return
                else:
                    self.logger.warning("连接池已关闭，重新初始化")
            # 对于 aiomysql，使用 closed 属性检查连接池状态
            elif hasattr(self.pool, 'closed'):
                if not self.pool.closed:
                    return
                else:
                    self.logger.warning("连接池已关闭，重新初始化")
            # 如果没有明确的关闭状态属性，假设连接池有效
            else:
                return

        async with self._pool_lock:
            if not self._pool_initialized:  # 双重检查避免竞争条件
                try:
                    # 使用单例连接池管理器
                    self.pool = await DatabaseConnectionPoolManager.get_mysql_pool(
                        pool_type='asyncmy',
                        host=self.settings.get('MYSQL_HOST', 'localhost'),
                        port=self.settings.get_int('MYSQL_PORT', 3306),
                        user=self.settings.get('MYSQL_USER', 'root'),
                        password=self.settings.get('MYSQL_PASSWORD', ''),
                        db=self.settings.get('MYSQL_DB', 'scrapy_db'),
                        minsize=self.settings.get_int('MYSQL_POOL_MIN', 3),
                        maxsize=self.settings.get_int('MYSQL_POOL_MAX', 10),
                        echo=self.settings.get_bool('MYSQL_ECHO', False)
                    )
                    self._pool_initialized = True
                    self.logger.info(
                        f"MySQL连接池初始化完成（表: {self.table_name}, 使用全局共享连接池）"
                    )
                except Exception as e:
                    self.logger.error(f"MySQL连接池初始化失败: {e}")
                    # 重置状态以便重试
                    self._pool_initialized = False
                    self.pool = None
                    raise

    async def _execute_sql(self, sql: str, values: Optional[list] = None) -> int:
        """执行SQL语句并处理结果，包含死锁重试机制"""
        max_retries = 3
        timeout = 30  # 30秒超时
        
        for attempt in range(max_retries):
            try:
                # 检查连接池状态
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")
                
                # 使用asyncmy的连接方式，带超时
                async with async_timeout.timeout(timeout):
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            # 根据是否有参数值选择不同的执行方法
                            if values is not None:
                                rowcount = await cursor.execute(sql, values)
                            else:
                                rowcount = await cursor.execute(sql)

                            await conn.commit()
                            return rowcount or 0
            except asyncio.TimeoutError:
                self.logger.error(f"执行SQL超时 ({timeout}秒): {sql[:100]}...")
                raise ItemDiscard(f"MySQL操作超时: {sql[:100]}...")
            except Exception as e:
                # 检查是否是死锁错误
                if "Deadlock found" in str(e) and attempt < max_retries - 1:
                    self.logger.warning(f"检测到死锁，正在进行第 {attempt + 1} 次重试: {str(e)}")
                    await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避
                    continue
                # 检查是否是连接错误，尝试重新初始化连接池
                elif ("Connection closed" in str(e) or "Lost connection" in str(e)) and attempt < max_retries - 1:
                    self.logger.warning(f"检测到连接错误，尝试重新初始化连接池并重试: {str(e)}")
                    self._pool_initialized = False
                    self.pool = None
                    await asyncio.sleep(0.5 * (attempt + 1))  # 简单退避
                    continue
                else:
                    # 添加更多调试信息
                    error_msg = f"MySQL插入失败: {str(e)}"
                    self.logger.error(f"执行SQL时发生错误: {error_msg}")
                    # 如果是批量操作，记录SQL和值以便调试
                    if values:
                        self.logger.debug(f"SQL: {sql[:200]}..., Values: {values[:5] if isinstance(values, list) else '...'}")
                    raise ItemDiscard(error_msg)
        return 0

    async def _execute_batch_sql(self, sql: str, values_list: list) -> int:
        """执行批量SQL语句，包含死锁重试机制"""
        max_retries = 3
        timeout = 60  # 60秒超时，批量操作可能需要更长时间
        
        for attempt in range(max_retries):
            try:
                # 检查连接池状态
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")
                
                # 带超时的批量执行
                async with async_timeout.timeout(timeout):
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            # 执行批量插入
                            rowcount = await cursor.executemany(sql, values_list)
                            await conn.commit()
                            return rowcount or 0
            except asyncio.TimeoutError:
                self.logger.error(f"执行批量SQL超时 ({timeout}秒)")
                raise ItemDiscard(f"MySQL批量操作超时")
            except Exception as e:
                # 检查是否是死锁错误
                if "Deadlock found" in str(e) and attempt < max_retries - 1:
                    self.logger.warning(f"检测到批量插入死锁，正在进行第 {attempt + 1} 次重试: {str(e)}")
                    await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避
                    continue
                # 检查是否是连接错误，尝试重新初始化连接池
                elif ("Connection closed" in str(e) or "Lost connection" in str(e)) and attempt < max_retries - 1:
                    self.logger.warning(f"检测到连接错误，尝试重新初始化连接池并重试: {str(e)}")
                    self._pool_initialized = False
                    self.pool = None
                    await asyncio.sleep(0.5 * (attempt + 1))  # 简单退避
                    continue
                else:
                    # 添加更多调试信息
                    error_msg = f"MySQL批量插入失败: {str(e)}"
                    self.logger.error(f"执行批量SQL时发生错误: {error_msg}")
                    # 记录SQL和值的概要以便调试
                    self.logger.debug(f"SQL: {sql[:200]}..., Values count: {len(values_list) if isinstance(values_list, list) else 'unknown'}")
                    raise ItemDiscard(error_msg)
        return 0


class AiomysqlMySQLPipeline(BaseMySQLPipeline):
    """使用aiomysql库的MySQL管道实现"""
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger.info(f"创建AiomysqlMySQLPipeline实例，配置信息 - 主机: {self.settings.get('MYSQL_HOST', 'localhost')}, 数据库: {self.settings.get('MYSQL_DB', 'scrapy_db')}, 表名: {self.table_name}")

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    async def _ensure_pool(self):
        """延迟初始化连接池（线程安全）"""
        if self._pool_initialized and self.pool:
            # 检查连接池是否仍然有效
            # 对于 aiomysql，使用 closed 属性检查连接池状态
            if hasattr(self.pool, 'closed'):
                if not self.pool.closed:
                    return
                else:
                    self.logger.warning("连接池已关闭，重新初始化")
            # 对于 asyncmy，使用 _closed 属性检查连接池状态
            elif hasattr(self.pool, '_closed'):
                if not self.pool._closed:
                    return
                else:
                    self.logger.warning("连接池已关闭，重新初始化")
            # 如果没有明确的关闭状态属性，假设连接池有效
            else:
                return

        async with self._pool_lock:
            if not self._pool_initialized:
                try:
                    # 使用单例连接池管理器
                    self.pool = await DatabaseConnectionPoolManager.get_mysql_pool(
                        pool_type='aiomysql',
                        host=self.settings.get('MYSQL_HOST', 'localhost'),
                        port=self.settings.get_int('MYSQL_PORT', 3306),
                        user=self.settings.get('MYSQL_USER', 'root'),
                        password=self.settings.get('MYSQL_PASSWORD', ''),
                        db=self.settings.get('MYSQL_DB', 'scrapy_db'),
                        minsize=self.settings.get_int('MYSQL_POOL_MIN', 2),
                        maxsize=self.settings.get_int('MYSQL_POOL_MAX', 5)
                    )
                    self._pool_initialized = True
                    self.logger.info(
                        f"MySQL连接池初始化完成（表: {self.table_name}, 使用全局共享连接池）"
                    )
                except Exception as e:
                    self.logger.error(f"Aiomysql连接池初始化失败: {e}")
                    # 重置状态以便重试
                    self._pool_initialized = False
                    self.pool = None
                    raise

    async def _execute_sql(self, sql: str, values: Optional[list] = None) -> int:
        """执行SQL语句并处理结果，包含死锁重试机制"""
        max_retries = 3
        timeout = 30  # 统一超时设置
        
        for attempt in range(max_retries):
            try:
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")

                # 添加超时控制
                async with async_timeout.timeout(timeout):
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            if values is not None:
                                rowcount = await cursor.execute(sql, values)
                            else:
                                rowcount = await cursor.execute(sql)
                            await conn.commit()
                            return rowcount or 0
                            
            except asyncio.TimeoutError:
                self.logger.error(f"Aiomysql 执行SQL超时 ({timeout}秒)")
                raise ItemDiscard(f"MySQL操作超时")
            except Exception as e:
                # 统一异常转字符串处理，防止 e 为非标准异常时报错
                err_str = str(e)
                # 死锁重试
                if "Deadlock found" in err_str and attempt < max_retries - 1:
                    self.logger.warning(f"检测到死锁，正在进行第 {attempt + 1} 次重试: {err_str}")
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
                # 断连重试 (aiomysql 抛出的通常是 OperationalError)
                elif ("2006" in err_str or "2013" in err_str or "lost connection" in err_str.lower()) and attempt < max_retries - 1:
                     self.logger.warning(f"检测到连接丢失，尝试重试: {err_str}")
                     # 可以在这里尝试手动无效化池（如果管理器支持），或者直接依赖池的自动重连
                     await asyncio.sleep(0.5 * (attempt + 1))
                     continue
                else:
                    error_msg = f"MySQL插入失败: {err_str}"
                    self.logger.error(f"执行SQL时发生错误: {error_msg}")
                    raise ItemDiscard(error_msg)
        return 0

    async def _execute_batch_sql(self, sql: str, values_list: list) -> int:
        """执行批量SQL语句，包含死锁重试机制"""
        max_retries = 3
        timeout = 60  # 批量操作超时设置
        
        for attempt in range(max_retries):
            try:
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")

                # 添加超时控制
                async with async_timeout.timeout(timeout):
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            # 执行批量插入
                            rowcount = await cursor.executemany(sql, values_list)
                            await conn.commit()
                            return rowcount or 0
                            
            except asyncio.TimeoutError:
                self.logger.error(f"Aiomysql 执行批量SQL超时 ({timeout}秒)")
                raise ItemDiscard(f"MySQL批量操作超时")
            except Exception as e:
                # 统一异常转字符串处理，防止 e 为非标准异常时报错
                err_str = str(e)
                # 死锁重试
                if "Deadlock found" in err_str and attempt < max_retries - 1:
                    self.logger.warning(f"检测到批量插入死锁，正在进行第 {attempt + 1} 次重试: {err_str}")
                    await asyncio.sleep(0.1 * (2 ** attempt))
                    continue
                # 断连重试 (aiomysql 抛出的通常是 OperationalError)
                elif ("2006" in err_str or "2013" in err_str or "lost connection" in err_str.lower()) and attempt < max_retries - 1:
                     self.logger.warning(f"检测到连接丢失，尝试重试: {err_str}")
                     # 可以在这里尝试手动无效化池（如果管理器支持），或者直接依赖池的自动重连
                     await asyncio.sleep(0.5 * (attempt + 1))
                     continue
                else:
                    error_msg = f"MySQL批量插入失败: {err_str}"
                    self.logger.error(f"执行批量SQL时发生错误: {error_msg}")
                    raise ItemDiscard(error_msg)
        return 0
