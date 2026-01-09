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
        
        # 设置连接池类型标识
        self.pool_type = 'asyncmy' if 'Asyncmy' in self.__class__.__name__ else 'aiomysql'
            
    @staticmethod
    def _is_pool_active(pool):
        """检查连接池是否活跃 - 统一处理 aiomysql 和 asyncmy 的差异"""
        if not pool:
            return False
            
        # 对于 asyncmy，使用 _closed 属性检查连接池状态
        if hasattr(pool, '_closed'):
            return not pool._closed
        # 对于 aiomysql，使用 closed 属性检查连接池状态
        elif hasattr(pool, 'closed'):
            return not pool.closed
        # 如果没有明确的关闭状态属性，假设连接池有效
        else:
            return True
                
    @staticmethod
    def _is_conn_active(conn):
        """检查连接是否活跃 - 统一处理 aiomysql 和 asyncmy 的差异"""
        if not conn:
            return False
            
        # 对于 asyncmy，使用 _closed 属性检查连接状态
        if hasattr(conn, '_closed'):
            return not conn._closed
        # 对于 aiomysql，使用 closed 属性检查连接状态
        elif hasattr(conn, 'closed'):
            return not conn.closed
        # 如果没有明确的关闭状态属性，假设连接有效
        else:
            return True
            
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
                insert_ignore=self.insert_ignore,
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
                        # 【新增】批量执行失败时，尝试降级为单条插入以挽救数据
                        self.logger.warning(f"批量执行失败，尝试降级为单条插入: {e}")
                        rowcount = await self._execute_batch_as_individual(current_batch)
                
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
    
    async def _execute_batch_as_individual(self, datas: List[Dict]) -> int:
        """将批量数据降级为单条执行，以挽救数据"""
        total_rows = 0
        failed_count = 0
        
        for i, data in enumerate(datas):
            try:
                # 获取单条 SQL
                sql, params = SQLBuilder.make_insert(
                    table=self.table_name,
                    data=data,
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore,
                    prefer_alias=self.settings.get_bool('MYSQL_PREFER_ALIAS', True)
                )
                rowcount = await self._execute_sql(sql, params)
                total_rows += rowcount or 0
            except Exception as row_err:
                failed_count += 1
                self.logger.error(f"单条插入也失败 (第{i+1}/{len(datas)}条): {row_err}")
                
        self.logger.info(f"降级执行完成: 成功 {len(datas)-failed_count} 条, 失败 {failed_count} 条, 影响 {total_rows} 行")
        return total_rows

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
            
        # 释放对连接池的引用，以便在事件循环关闭前进行垃圾回收
        # 这有助于避免 "RuntimeError: Event loop is closed" 错误（尤其是在Linux上）
        self.pool = None
        self._pool_initialized = False
            
        # 清空缓冲区
        self.batch_buffer.clear()
            
        # 注意：不再关闭连接池，因为连接池是全局共享的
        # 连接池的关闭由 DatabaseConnectionPoolManager.close_all_mysql_pools() 统一管理
        self.logger.info(
            f"MySQL Pipeline {self.__class__.__name__} 已关闭并释放资源"
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
    
    async def _close_conn_properly(self, conn):
        """安全关闭连接，避免事件循环已关闭时的问题"""
        try:
            # 检查事件循环状态，避免在事件循环关闭后尝试异步操作
            try:
                loop = asyncio.get_event_loop()
                loop_is_closed = loop.is_closed()
            except RuntimeError:
                # 没有运行中的事件循环
                loop_is_closed = True
            
            if loop_is_closed:
                # 事件循环已关闭，只能尝试同步关闭
                if hasattr(conn, '_writer'):
                    conn._writer.close()
                if hasattr(conn, 'close'):
                    conn.close()
                return
            
            # 事件循环仍在运行，可以执行异步关闭
            if hasattr(conn, 'close'):
                conn.close()
            if hasattr(conn, 'ensure_closed'):
                await conn.ensure_closed()
                
        except Exception:
            # 忽略所有关闭错误
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
        if self._pool_initialized and self.pool and self._is_pool_active(self.pool):
            return
        elif self._pool_initialized and self.pool:
            self.logger.warning("连接池已初始化但无效，重新初始化")

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
        """执行SQL语句并处理结果，包含死锁重试和连接同步修复"""
        max_retries = 3
        timeout = 60  # 增加超时时间，处理大文本数据

        for attempt in range(max_retries):
            conn = None
            try:
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")

                async with async_timeout.timeout(timeout):
                    # 1. 手动获取连接，而不是直接用 async with pool.acquire()
                    conn = await self.pool.acquire()

                    # 2. 检查连接是否仍然活跃
                    if not self._is_conn_active(conn):
                        self.logger.warning("获取的连接已失效，可能需要重新获取")
                        if conn:
                            await self.pool.release(conn)
                        continue # 重试
                    
                    # 3. 显式开启事务（部分驱动在execute时自动开启，但这里确护持干净）
                    async with conn.cursor() as cursor:
                        try:
                            if values is not None:
                                rowcount = await cursor.execute(sql, values)
                            else:
                                rowcount = await cursor.execute(sql)

                            # 4. 成功则提交
                            await conn.commit()
                            return rowcount or 0
                        except Exception as e:
                            # 5. 【关键】失败必须显式回滚，清除该连接的待处理状态
                            await conn.rollback()
                            raise e

            except asyncio.TimeoutError:
                self.logger.error(f"MySQL操作超时: {sql[:100]}...")
                # 超时可能导致同步错乱，建议断开该连接
                if conn:
                    await self._close_conn_properly(conn)
                raise ItemDiscard("MySQL操作超时")

            except Exception as e:
                err_str = str(e)
                # 6. 【关键】处理 2014 错误：如果报错同步问题，强制销毁连接
                if "2014" in err_str or "Command Out of Sync" in err_str:
                    self.logger.warning(f"检测到脏连接(2014)，正在丢弃并重试: {err_str}")
                    if conn:
                        await self._close_conn_properly(conn)
                        conn = None # 标记为None，防止 finally 里再次 release
                    continue # 进入下一次重试，重试会拿新连接

                # 其他常见重试逻辑（死锁、断连）
                if ("Deadlock found" in err_str or "2006" in err_str) and attempt < max_retries - 1:
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue

                # 最终失败处理
                self.logger.error(f"SQL执行最终失败: {err_str}")
                raise ItemDiscard(f"MySQL插入失败: {err_str}")

            finally:
                # 7. 归还连接给池
                if conn:
                    await self.pool.release(conn)
        return 0

    async def _execute_batch_sql(self, sql: str, values_list: list) -> int:
        """批量执行核心，带自动降级"""
        try:
            # 高性能模式：因为 SQLBuilder 已经拼好了多行占位符，这里直接用 execute
            max_retries = 3
            timeout = 60  # 60秒超时，批量操作可能需要更长时间

            for attempt in range(max_retries):
                conn = None
                try:
                    if not self.pool:
                        raise RuntimeError("Database connection pool is not available")
            
                    async with async_timeout.timeout(timeout):
                        # 1. 手动获取连接，而不是直接用 async with pool.acquire()
                        conn = await self.pool.acquire()
            
                        # 2. 检查连接是否仍然活跃
                        if not self._is_conn_active(conn):
                            self.logger.warning("获取的连接已失效，可能需要重新获取")
                            if conn:
                                await self.pool.release(conn)
                            continue # 重试
                                
                        # 3. 显式开启事务（部分驱动在execute时自动开启，但这里确保护持干净）
                        async with conn.cursor() as cursor:
                            try:
                                # 执行批量插入 - 使用execute而不是executemany，避免2014错误
                                rowcount = await cursor.execute(sql, values_list)
            
                                # 【关键修复】排空潜在结果集，防止 2014
                                try:
                                    while await cursor.nextset():
                                        await cursor.fetchall()
                                except:
                                    pass
            
                                # 4. 成功则提交
                                await conn.commit()
                                return rowcount or 0
                            except Exception as e:
                                # 5. 【关键】失败必须显式回滚，清除该连接的待处理状态
                                await conn.rollback()
                                raise e

                except asyncio.TimeoutError:
                    self.logger.error(f"MySQL批量操作超时: {sql[:100]}...")
                    # 超时可能导致同步错乱，建议断开该连接
                    if conn:
                        await self._close_conn_properly(conn)
                    raise ItemDiscard("MySQL批量操作超时")

                except Exception as e:
                    err_str = str(e)
                    # 5. 【关键】处理 2014 错误：如果报错同步问题，强制销毁连接
                    if "2014" in err_str or "Command Out of Sync" in err_str:
                        self.logger.warning(f"检测到脏连接(2014)，正在丢弃并重试: {err_str}")
                        if conn:
                            await self._close_conn_properly(conn)
                            conn = None # 标记为None，防止 finally 里再次 release
                        continue # 进入下一次重试，重试会拿新连接

                    # 其他常见重试逻辑（死锁、断连）
                    if ("Deadlock found" in err_str or "2006" in err_str) and attempt < max_retries - 1:
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue

                    # 最终失败处理
                    self.logger.error(f"批量SQL执行最终失败: {err_str}")
                    raise ItemDiscard(f"MySQL批量插入失败: {err_str}")

                finally:
                    # 6. 归还连接给池
                    if conn:
                        await self.pool.release(conn)
            return 0
        
        except Exception as e:
            self.logger.warning(f"批量执行失败，尝试降级为单条循环执行以挽救数据: {e}")
            # 降级处理：从 self._flush_batch 中获取原始数据进行单条插入
            # 注意：这里无法直接访问原始数据，需要在调用处传递
            # 因此我们不在此处实现降级，而是让错误传播并由 _flush_batch 处理
            raise e


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
        if self._pool_initialized and self.pool and self._is_pool_active(self.pool):
            return
        elif self._pool_initialized and self.pool:
            self.logger.warning("连接池已初始化但无效，重新初始化")

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
        """执行SQL语句并处理结果，包含死锁重试和连接同步修复"""
        max_retries = 3
        timeout = 60  # 增加超时时间，处理大文本数据

        for attempt in range(max_retries):
            conn = None
            try:
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")

                async with async_timeout.timeout(timeout):
                    # 1. 手动获取连接，而不是直接用 async with pool.acquire()
                    conn = await self.pool.acquire()

                    # 2. 检查连接是否仍然活跃
                    if not self._is_conn_active(conn):
                        self.logger.warning("获取的连接已失效，可能需要重新获取")
                        if conn:
                            await self.pool.release(conn)
                        continue # 重试
                    
                    # 3. 显式开启事务（部分驱动在execute时自动开启，但这里确保护持干净）
                    async with conn.cursor() as cursor:
                        try:
                            if values is not None:
                                rowcount = await cursor.execute(sql, values)
                            else:
                                rowcount = await cursor.execute(sql)

                            # 4. 成功则提交
                            await conn.commit()
                            return rowcount or 0
                        except Exception as e:
                            # 5. 【关键】失败必须显式回滚，清除该连接的待处理状态
                            await conn.rollback()
                            raise e

            except asyncio.TimeoutError:
                self.logger.error(f"MySQL操作超时: {sql[:100]}...")
                # 超时可能导致同步错乱，建议断开该连接
                if conn:
                    await self._close_conn_properly(conn)
                raise ItemDiscard("MySQL操作超时")

            except Exception as e:
                err_str = str(e)
                # 6. 【关键】处理 2014 错误：如果报错同步问题，强制销毁连接
                if "2014" in err_str or "Command Out of Sync" in err_str:
                    self.logger.warning(f"检测到脏连接(2014)，正在丢弃并重试: {err_str}")
                    if conn:
                        await self._close_conn_properly(conn)
                        conn = None # 标记为None，防止 finally 里再次 release
                    continue # 进入下一次重试，重试会拿新连接

                # 其他常见重试逻辑（死锁、断连）
                if ("Deadlock found" in err_str or "2006" in err_str or "2013" in err_str or "lost connection" in err_str.lower()) and attempt < max_retries - 1:
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue

                # 最终失败处理
                self.logger.error(f"SQL执行最终失败: {err_str}")
                raise ItemDiscard(f"MySQL插入失败: {err_str}")

            finally:
                # 7. 归还连接给池
                if conn:
                    await self.pool.release(conn)
        return 0

    async def _execute_batch_sql(self, sql: str, values_list: list) -> int:
        """批量执行核心，带自动降级"""
        try:
            # 高性能模式：因为 SQLBuilder 已经拼好了多行占位符，这里直接用 execute
            max_retries = 3
            timeout = 60  # 60秒超时，批量操作可能需要更长时间

            for attempt in range(max_retries):
                conn = None
                try:
                    if not self.pool:
                        raise RuntimeError("Database connection pool is not available")

                    async with async_timeout.timeout(timeout):
                        # 1. 手动获取连接，而不是直接用 async with pool.acquire()
                        conn = await self.pool.acquire()

                        # 2. 检查连接是否仍然活跃
                        if not self._is_conn_active(conn):
                            self.logger.warning("获取的连接已失效，可能需要重新获取")
                            if conn:
                                await self.pool.release(conn)
                            continue # 重试
                        
                        # 3. 显式开启事务（部分驱动在execute时自动开启，但这里确保护持干净）
                        async with conn.cursor() as cursor:
                            try:
                                # 执行批量插入 - 使用execute而不是executemany，避免2014错误
                                rowcount = await cursor.execute(sql, values_list)

                                # 【关键修复】排空潜在结果集，防止 2014
                                try:
                                    while await cursor.nextset():
                                        await cursor.fetchall()
                                except:
                                    pass

                                # 4. 成功则提交
                                await conn.commit()
                                return rowcount or 0
                            except Exception as e:
                                # 5. 【关键】失败必须显式回滚，清除该连接的待处理状态
                                await conn.rollback()
                                raise e

                except asyncio.TimeoutError:
                    self.logger.error(f"MySQL批量操作超时: {sql[:100]}...")
                    # 超时可能导致同步错乱，建议断开该连接
                    if conn:
                        await self._close_conn_properly(conn)
                    raise ItemDiscard("MySQL批量操作超时")

                except Exception as e:
                    err_str = str(e)
                    # 6. 【关键】处理 2014 错误：如果报错同步问题，强制销毁连接
                    if "2014" in err_str or "Command Out of Sync" in err_str:
                        self.logger.warning(f"检测到脏连接(2014)，正在丢弃并重试: {err_str}")
                        if conn:
                            await self._close_conn_properly(conn)
                            conn = None # 标记为None，防止 finally 里再次 release
                        continue # 进入下一次重试，重试会拿新连接

                    # 其他常见重试逻辑（死锁、断连）
                    if ("Deadlock found" in err_str or "2006" in err_str or "2013" in err_str or "lost connection" in err_str.lower()) and attempt < max_retries - 1:
                        await asyncio.sleep(0.2 * (attempt + 1))
                        continue

                    # 最终失败处理
                    self.logger.error(f"批量SQL执行最终失败: {err_str}")
                    raise ItemDiscard(f"MySQL批量插入失败: {err_str}")

                finally:
                    # 7. 归还连接给池
                    if conn:
                        await self.pool.release(conn)
            return 0
        
        except Exception as e:
            self.logger.warning(f"批量执行失败，尝试降级为单条循环执行以挽救数据: {e}")
            # 降级处理：从 self._flush_batch 中获取原始数据进行单条插入
            # 注意：这里无法直接访问原始数据，需要在调用处传递
            # 因此我们不在此处实现降级，而是让错误传播并由 _flush_batch 处理
            raise e
