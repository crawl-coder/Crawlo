# -*- coding: utf-8 -*-
import re
import asyncio
import async_timeout
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.db_helper import SQLBuilder
from crawlo.utils.resource_manager import ResourceType
from crawlo.utils.mysql_connection_pool import (
    AiomysqlConnectionPoolManager,
    AsyncmyConnectionPoolManager,
    is_pool_active
)
from . import ResourceManagedPipeline


class BaseMySQLPipeline(ResourceManagedPipeline, ABC):
    """MySQL管道的基类，封装公共功能
    
    支持异步数据库操作，提供批量插入、错误重试、连接池管理等功能。
    """
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.crawler = crawler
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)

        # 记录管道初始化
        self.logger.debug(f"MySQL管道初始化完成: {self.__class__.__name__}")

        # 使用异步锁和初始化标志确保线程安全
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        
        # 初始化配置
        self._init_config()
        
        # 批量插入相关
        self.batch_buffer: List[Dict] = []  # 批量缓冲区
        self._batch_timer_handle = None  # 定时刷新处理器
        

        
        # 新增配置项
        self.batch_timeout = self.settings.get_int('MYSQL_BATCH_TIMEOUT', 120)  # 批量操作超时时间，默认120秒
        self.health_check_interval = self.settings.get_float('MYSQL_HEALTH_CHECK_INTERVAL', 120.0)  # 连接池健康检查间隔，默认120秒
        self.pool_repair_attempts = self.settings.get_int('MYSQL_POOL_REPAIR_ATTEMPTS', 3)  # 连接池修复尝试次数，默认3次
        
        # 配置项说明:
        # MYSQL_BATCH_SIZE: 批量插入的大小，默认100
        # MYSQL_USE_BATCH: 是否启用批量插入，默认False
        # MYSQL_EXECUTE_MAX_RETRIES: SQL执行最大重试次数，默认3
        # MYSQL_EXECUTE_TIMEOUT: SQL执行超时时间（秒），默认60
        # MYSQL_EXECUTE_RETRY_DELAY: 重试之间的延迟系数，默认0.2
        # MYSQL_BATCH_TIMEOUT: 批量操作超时时间（秒），默认120
        # MYSQL_HEALTH_CHECK_INTERVAL: 连接池健康检查间隔（秒），默认60
        # MYSQL_POOL_REPAIR_ATTEMPTS: 连接池修复尝试次数，默认3
        
        # 健康检查相关
        self._health_check_timer_handle = None  # 健康检查定时器
        
        # 设置连接池类型标识
        self.pool_type = 'asyncmy' if 'Asyncmy' in self.__class__.__name__ else 'aiomysql'
            
    def _init_config(self):
        """初始化配置项"""
        # 表名配置
        spider_table_name = None
        if hasattr(self.crawler, 'spider') and self.crawler.spider and hasattr(self.crawler.spider, 'custom_settings'):
            spider_table_name = self.crawler.spider.custom_settings.get('MYSQL_TABLE')
            
        self.table_name = (
                spider_table_name or
                self.settings.get('MYSQL_TABLE') or
                getattr(self.crawler.spider, 'mysql_table', None) or
                f"{getattr(self.crawler.spider, 'name', 'default')}_items"
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
        
        # 连接池和执行配置
        self.execute_max_retries = self.settings.get_int('MYSQL_EXECUTE_MAX_RETRIES', 3)
        self.execute_timeout = self.settings.get_int('MYSQL_EXECUTE_TIMEOUT', 60)
        self.execute_retry_delay = self.settings.get_float('MYSQL_EXECUTE_RETRY_DELAY', 0.2)
        
        # SQL生成配置
        self.auto_update = self.settings.get_bool('MYSQL_AUTO_UPDATE', False)
        self.insert_ignore = self.settings.get_bool('MYSQL_INSERT_IGNORE', False)
        self.update_columns = self.settings.get('MYSQL_UPDATE_COLUMNS', ())
        
        # MySQL别名语法配置：True使用AS `alias`语法，False使用`table`.`column`语法
        self.prefer_alias_syntax = self.settings.get_bool('MYSQL_PREFER_ALIAS_SYNTAX', True)
        
        # 验证 update_columns 是否为元组或列表
        if self.update_columns and not isinstance(self.update_columns, (tuple, list)):
            self.logger.warning(f"更新列配置应该是一个元组或列表，当前类型为 {type(self.update_columns)}。已自动转换为元组。")
            self.update_columns = (self.update_columns,)
            
    def _validate_config(self) -> bool:
        """验证配置项的有效性
        
        Returns:
            bool: 配置是否有效
        """
        # 检查必要配置
        required_configs = [
            ('MYSQL_HOST', self.settings.get('MYSQL_HOST', 'localhost')),
            ('MYSQL_DB', self.settings.get('MYSQL_DB', 'scrapy_db')),
            ('MYSQL_USER', self.settings.get('MYSQL_USER', 'root')),
        ]
        
        for config_name, config_value in required_configs:
            if not config_value:
                self.logger.error(f"缺少必需的配置项: {config_name}")
                return False
        
        return True
            
    @staticmethod
    def _is_pool_active(pool):
        """检查连接池是否活跃 - 统一处理 aiomysql 和 asyncmy 的差异
        
        Args:
            pool: 数据库连接池对象
            
        Returns:
            bool: 连接池是否活跃
        """
        return is_pool_active(pool)
                
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
            
        # 确保资源已初始化
        await self._ensure_initialized()
        

            
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
                    self.logger.debug(
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

    async def _execute_sql(self, sql: str, values: Optional[list] = None) -> int:
        """执行SQL语句并处理结果"""
        max_retries = self.execute_max_retries
        timeout = self.settings.get_int('MYSQL_EXECUTE_TIMEOUT', 60)
        
        # 开始时间用于计算延迟
        start_time = asyncio.get_event_loop().time()
        
        for attempt in range(max_retries):
            conn = None
            try:
                if not self.pool:
                    raise RuntimeError("Database connection pool is not available")
                
                # 检查连接池是否活跃
                if not self._is_pool_active(self.pool):
                    self.logger.warning("Connection pool is closed, attempting to reinitialize")
                    # 尝试重新初始化连接池
                    self._pool_initialized = False
                    await self._ensure_pool()
                    if not self.pool or not self._is_pool_active(self.pool):
                        raise RuntimeError("Failed to reinitialize database connection pool")

                async with async_timeout.timeout(timeout):
                    conn = await self.pool.acquire()

                # 检查连接是否仍然活跃
                if not self._is_conn_active(conn):
                    self.logger.warning("获取的连接已失效，可能需要重新获取")
                    if conn:
                        await self.pool.release(conn)
                    continue # 重试
                
                # 执行SQL并处理事务
                rowcount = await self._execute_sql_with_transaction(conn, sql, values)
                
                # 记录执行时间
                execution_time = asyncio.get_event_loop().time() - start_time
                self.crawler.stats.inc_value('mysql/sql_execution_time', execution_time)
                
                return rowcount

            except asyncio.TimeoutError:
                self.logger.error(f"MySQL操作超时: {sql[:100]}...")
                if conn:
                    await self._close_conn_properly(conn)
                raise ItemDiscard("MySQL操作超时")

            except Exception as e:
                if await self._handle_common_exceptions(e, attempt, max_retries, conn):
                    # 记录重试次数
                    self.crawler.stats.inc_value('mysql/retry_count')
                    continue  # 继续重试
                else:
                    # 最终失败处理
                    err_str = str(e)
                    self.logger.error(f"SQL执行最终失败: {err_str}")
                    raise ItemDiscard(f"MySQL插入失败: {err_str}")

            finally:
                # 归还连接给池
                if conn:
                    await self.pool.release(conn)
        return 0

    async def _execute_batch_sql(self, sql: str, values_list: list) -> int:
        """批量执行核心，带自动降级"""
        # 开始时间用于计算延迟
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 高性能模式：因为 SQLBuilder 已经拼好了多行占位符，这里直接用 execute
            max_retries = self.execute_max_retries
            timeout = self.batch_timeout  # 使用批量专用超时配置

            for attempt in range(max_retries):
                conn = None
                try:
                    if not self.pool:
                        raise RuntimeError("Database connection pool is not available")

                    # 记录连接获取开始时间
                    acquire_start_time = asyncio.get_event_loop().time()
                    async with async_timeout.timeout(timeout):
                        conn = await self.pool.acquire()
                    # 记录连接获取等待时间
                    acquire_wait_time = asyncio.get_event_loop().time() - acquire_start_time
                    self.crawler.stats.inc_value('mysql/connection_acquire_time', acquire_wait_time)

                    # 检查连接是否仍然活跃
                    if not self._is_conn_active(conn):
                        self.logger.warning(f"获取的连接已失效，可能需要重新获取 - SQL: {sql[:100]}...")
                        if conn:
                            await self.pool.release(conn)
                        continue # 重试
                        
                    # 执行批量SQL并处理事务
                    rowcount = await self._execute_batch_sql_with_transaction(conn, sql, values_list)
                    
                    # 记录执行时间
                    execution_time = asyncio.get_event_loop().time() - start_time
                    self.crawler.stats.inc_value('mysql/batch_execution_time', execution_time)
                    
                    self.logger.debug(f"批量SQL执行成功 - 影响行数: {rowcount}, 执行时间: {execution_time:.3f}s, SQL: {sql[:100]}...")
                    
                    return rowcount

                except asyncio.TimeoutError:
                    self.logger.error(f"MySQL批量操作超时: {sql[:100]}..., 超时阈值: {timeout}s")
                    if conn:
                        await self._close_conn_properly(conn)
                    raise ItemDiscard("MySQL批量操作超时")

                except Exception as e:
                    if await self._handle_common_exceptions(e, attempt, max_retries, conn):
                        # 记录重试次数
                        self.crawler.stats.inc_value('mysql/batch_retry_count')
                        self.logger.warning(f"批量SQL执行失败，准备重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                        continue  # 继续重试
                    else:
                        # 最终失败处理
                        err_str = str(e)
                        self.logger.error(f"批量SQL执行最终失败: {err_str}, SQL: {sql[:100]}...")
                        raise ItemDiscard(f"MySQL批量插入失败: {err_str}")

                finally:
                    # 归还连接给池
                    if conn:
                        await self.pool.release(conn)
                        # 记录连接池使用率
                        if hasattr(self.pool, 'size') and hasattr(self.pool, 'minsize'):
                            try:
                                pool_size = getattr(self.pool, 'size', 0)
                                pool_acquired = getattr(self.pool, 'acquired', 0)
                                pool_usage = (pool_acquired / max(pool_size, 1)) * 100 if pool_size > 0 else 0
                                self.crawler.stats.inc_value('mysql/pool_usage_percent', pool_usage)
                            except:
                                pass  # 忽略统计错误
            return 0
        
        except Exception as e:
            # 记录批量执行失败次数
            self.crawler.stats.inc_value('mysql/batch_failure_count')
            self.logger.warning(f"批量执行失败，将在_flush_batch中进行降级处理: {e}, SQL: {sql[:100]}...")
            
            # 降级处理：由于在_execute_batch_sql方法中无法直接访问原始数据字典列表，
            # 所以降级处理主要在_flush_batch方法中实现，这里只是记录和传递异常
            self.logger.debug(f"批量执行失败，异常将传递给_flush_batch进行降级处理")
            raise e

    async def _flush_batch(self, spider_name: str):
        """刷新批量缓冲区并执行批量插入"""
        # 确保资源已初始化
        await self._ensure_initialized()
        
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
                prefer_alias=self.prefer_alias_syntax
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
                            prefer_alias=not self.prefer_alias_syntax
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
    
    async def _start_health_check_timer(self):
        """启动健康检查定时器"""
        if self._health_check_timer_handle is not None:
            self._health_check_timer_handle.cancel()
        
        # 创建健康检查任务
        self._health_check_timer_handle = asyncio.create_task(self._health_check_periodically())
    
    async def _health_check_periodically(self):
        """定期执行健康检查"""
        failure_count = 0
        max_failures = 3  # 连续失败3次才标记不可用
        
        while True:
            try:
                # 等待指定间隔
                await asyncio.sleep(self.health_check_interval)
                
                # 执行健康检查
                is_healthy = await self._health_check_pool()
                
                if not is_healthy:
                    failure_count += 1
                    self.logger.warning(f"连接池健康检查失败 ({failure_count}/{max_failures})，尝试修复连接池 (类型: {self.pool_type})")
                    
                    if failure_count >= max_failures:
                        # 尝试修复连接池
                        await self._check_and_repair_pool()
                        failure_count = 0  # 重置失败计数
                        
                        # 更新健康检查统计
                        self.crawler.stats.inc_value('mysql/pool_repaired')
                else:
                    failure_count = 0  # 重置失败计数
                    # 更新健康状态统计
                    self.crawler.stats.inc_value('mysql/pool_health_checks')
            except asyncio.CancelledError:
                # 任务被取消，退出循环
                break
            except Exception as e:
                self.logger.error(f"健康检查任务出错: {e}")
                # 继续循环，避免任务结束
                continue
    
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
                    prefer_alias=self.prefer_alias_syntax
                )
                rowcount = await self._execute_sql(sql, params)
                total_rows += rowcount or 0
            except Exception as row_err:
                failed_count += 1
                self.logger.error(f"单条插入也失败 (第{i+1}/{len(datas)}条): {row_err}")
                
        self.logger.info(f"降级执行完成: 成功 {len(datas)-failed_count} 条, 失败 {failed_count} 条, 影响 {total_rows} 行")
        return total_rows

    async def _create_table(self):
        """创建数据表（如果不存在）"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 创建表的SQL语句，使用CREATE TABLE IF NOT EXISTS
                    create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS `{self.table_name}` (
                        `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                        `title` VARCHAR(255) NOT NULL,
                        `publish_time` DATETIME,
                        `url` VARCHAR(255) NOT NULL UNIQUE,
                        `source` VARCHAR(100),
                        `content` TEXT,
                        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX `idx_url` (`url`),
                        INDEX `idx_publish_time` (`publish_time`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                    await cursor.execute(create_table_sql)
                    await conn.commit()
                    self.logger.debug(f"表 {self.table_name} 检查/创建完成")
        except Exception as e:
            self.logger.warning(f"表 {self.table_name} 创建失败（可能已存在）: {e}")
    
    async def _initialize_resources(self):
        """初始化连接池资源并注册到资源管理器"""
        # 确保连接池已初始化
        await self._ensure_pool()
        
        # 创建表（如果不存在）
        await self._create_table()
            
        # 将连接池注册到资源管理器，以便在爬虫关闭时自动清理
        if self.pool:
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                resource_type=ResourceType.PIPELINE,  # 使用PIPELINE类型表示数据库连接池
                name=f"mysql_{self.pool_type}_pool"
            )
            
        # 启动健康检查定时器（添加延迟确保连接池完全就绪）
        await asyncio.sleep(3)  # 等待3秒确保连接池完全就绪
        await self._start_health_check_timer()
            
        # 调用父类的初始化方法
        await super()._initialize_resources()
        
    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            if pool:
                pool.close()
                await pool.wait_closed()
                self.logger.info(f"{self.pool_type} MySQL连接池已关闭")
        except Exception as e:
            self.logger.error(f"关闭{self.pool_type} MySQL连接池时发生错误: {e}")
        
    async def _cleanup_resources(self):
        """清理资源"""
        # 在关闭前强制刷新剩余的批量数据
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name)
        
        # 清空批量缓冲区
        self.batch_buffer.clear()
        
        # 取消并清理批量刷新定时器（已移除，保留清理以防万一）
        if self._batch_timer_handle is not None:
            self._batch_timer_handle.cancel()
            try:
                await self._batch_timer_handle
            except asyncio.CancelledError:
                pass  # 任务已被取消，这是预期行为
            self._batch_timer_handle = None
            
        # 取消并清理健康检查定时器
        if self._health_check_timer_handle is not None:
            self._health_check_timer_handle.cancel()
            try:
                await self._health_check_timer_handle
            except asyncio.CancelledError:
                pass  # 任务已被取消，这是预期行为
            self._health_check_timer_handle = None
        
        # 重置初始化标志，确保下次执行时能正确重新初始化连接池
        self._pool_initialized = False
        self.pool = None
            
        # 调用父类的清理方法
        await super()._cleanup_resources()
        
            
    async def _make_insert_sql(self, item_dict: Dict, **kwargs) -> Tuple[str, List[Any]]:
        """生成插入SQL语句，子类可以重写此方法"""
        # 合并管道配置和传入的kwargs参数
        # 优先使用传入的prefer_alias参数，否则从设置中获取默认值
        prefer_alias = kwargs.pop('prefer_alias', self.prefer_alias_syntax)
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
    
    async def _check_and_repair_pool(self):
        """检查连接池健康状况并修复"""
        if not self.pool or not self._is_pool_active(self.pool):
            self.logger.warning("连接池不可用，正在重新初始化")
            self._pool_initialized = False
            await self._ensure_pool()
    
    async def _health_check_pool(self) -> bool:
        """执行连接池健康检查
        
        Returns:
            bool: 连接池是否健康
        """
        if not self.pool or not self._is_pool_active(self.pool):
            return False
        
        # 尝试获取连接并执行简单查询，最多尝试3次
        conn = None
        try:
            for attempt in range(3):  # 最多尝试3次
                try:
                    async with async_timeout.timeout(5):  # 增加超时时间到5秒
                        conn = await self.pool.acquire()
                        async with conn.cursor() as cursor:
                            await cursor.execute("SELECT 1")
                    return True
                except Exception as e:
                    if attempt < 2:
                        self.logger.debug(f"健康检查重试 {attempt+1}/2: {e}")
                        await asyncio.sleep(2)  # 增加重试间隔到2秒
                    else:
                        self.logger.warning(f"连接池健康检查失败: {e}")
                        return False
        finally:
            if conn:
                await self.pool.release(conn)
    
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
    
    async def _execute_sql_with_transaction(self, conn, sql: str, values: Optional[list] = None) -> int:
        """在事务中执行SQL
        
        Args:
            conn: 数据库连接对象
            sql: SQL语句
            values: SQL参数值列表
            
        Returns:
            int: 受影响的行数
            
        Raises:
            Exception: SQL执行失败时抛出异常
        """
        async with conn.cursor() as cursor:
            try:
                if values is not None:
                    rowcount = await cursor.execute(sql, values)
                else:
                    rowcount = await cursor.execute(sql)

                # 成功则提交
                await conn.commit()
                return rowcount or 0
            except Exception as e:
                # 失败必须显式回滚
                await conn.rollback()
                raise e
    
    async def _execute_batch_sql_with_transaction(self, conn, sql: str, values_list: list) -> int:
        """在事务中执行批量SQL
        
        Args:
            conn: 数据库连接对象
            sql: 批量SQL语句
            values_list: 批量参数值列表
            
        Returns:
            int: 受影响的行数
            
        Raises:
            Exception: SQL执行失败时抛出异常
        """
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

                # 成功则提交
                await conn.commit()
                return rowcount or 0
            except Exception as e:
                # 失败必须显式回滚
                await conn.rollback()
                raise e
    
    async def _handle_common_exceptions(self, e: Exception, attempt: int, max_retries: int, conn) -> bool:
        """统一处理常见异常，返回是否需要重试"""
        err_str = str(e).lower()  # 转换为小写以确保匹配
        
        # 处理 2014 错误：如果报错同步问题，强制销毁连接
        if "2014" in err_str or "command out of sync" in err_str:
            self.logger.warning(f"检测到脏连接(2014)，正在丢弃并重试: {err_str}")
            if conn:
                await self._close_conn_properly(conn)
                conn = None # 标记为None，防止在finally中再次release
            return True  # 需要重试

        # 其他常见重试逻辑（死锁、断连等）
        if (("deadlock found" in err_str or "2006" in err_str or 
             "2013" in err_str or "lost connection" in err_str) and 
            attempt < max_retries - 1):
            await asyncio.sleep(self.execute_retry_delay * (attempt + 1))
            return True  # 需要重试
        
        # 不需要重试，返回False
        return False
    



class AsyncmyMySQLPipeline(BaseMySQLPipeline):
    """使用asyncmy库的MySQL管道实现"""
    
    _instance = None
    _instance_lock = asyncio.Lock()
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger.info(f"创建AsyncmyMySQLPipeline实例，配置信息 - 主机: {self.settings.get('MYSQL_HOST', 'localhost')}, 数据库: {self.settings.get('MYSQL_DB', 'scrapy_db')}, 表名: {self.table_name}")

    @classmethod
    async def from_crawler(cls, crawler):
        async with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(crawler)
            return cls._instance

    async def _ensure_pool(self):
        """确保连接池已初始化（线程安全）"""
        # 检查事件循环是否已关闭
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                self.logger.warning("当前事件循环已关闭，无法初始化连接池")
                return
        except RuntimeError:
            # 没有运行中的事件循环
            self.logger.warning("没有运行中的事件循环，无法初始化连接池")
            return
        
        # 验证配置
        if not self._validate_config():
            raise ValueError("MySQL配置验证失败")
        
        if self._pool_initialized and self.pool and self._is_pool_active(self.pool):
            return
        elif self._pool_initialized and self.pool:
            self.logger.warning("连接池已初始化但无效，重新初始化")

        async with self._pool_lock:
            # 再次检查事件循环状态
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    self.logger.warning("在获取锁后，事件循环已关闭，无法初始化连接池")
                    return
            except RuntimeError:
                self.logger.warning("在获取锁后，没有运行中的事件循环，无法初始化连接池")
                return
                
            if not self._pool_initialized:  # 双重检查避免竞争条件
                try:
                    # 使用单例连接池管理器
                    self.pool = await AsyncmyConnectionPoolManager.get_pool(
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
                    self.logger.debug(
                        f"MySQL连接池初始化完成（表: {self.table_name}, 使用全局共享连接池）"
                    )
                except Exception as e:
                    self.logger.error(f"MySQL连接池初始化失败: {e}")
                    # 重置状态以便重试
                    self._pool_initialized = False
                    self.pool = None
                    raise

    # _execute_sql 和 _execute_batch_sql 方法继承自 BaseMySQLPipeline


    

class AiomysqlMySQLPipeline(BaseMySQLPipeline):
    """使用aiomysql库的MySQL管道实现"""
    
    _instance = None
    _instance_lock = asyncio.Lock()
    
    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger.info(f"创建AiomysqlMySQLPipeline实例，配置信息 - 主机: {self.settings.get('MYSQL_HOST', 'localhost')}, 数据库: {self.settings.get('MYSQL_DB', 'scrapy_db')}, 表名: {self.table_name}")

    @classmethod
    async def from_crawler(cls, crawler):
        async with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(crawler)
            return cls._instance

    async def _ensure_pool(self):
        """延迟初始化连接池（线程安全）"""
        # 检查事件循环是否已关闭
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                self.logger.warning("当前事件循环已关闭，无法初始化连接池")
                return
        except RuntimeError:
            # 没有运行中的事件循环
            self.logger.warning("没有运行中的事件循环，无法初始化连接池")
            return
        
        # 验证配置
        if not self._validate_config():
            raise ValueError("MySQL配置验证失败")
        
        if self._pool_initialized and self.pool and self._is_pool_active(self.pool):
            return
        elif self._pool_initialized and self.pool:
            self.logger.warning("连接池已初始化但无效，重新初始化")

        async with self._pool_lock:
            # 再次检查事件循环状态
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    self.logger.warning("在获取锁后，事件循环已关闭，无法初始化连接池")
                    return
            except RuntimeError:
                self.logger.warning("在获取锁后，没有运行中的事件循环，无法初始化连接池")
                return
                
            if not self._pool_initialized:
                try:
                    # 使用单例连接池管理器
                    self.pool = await AiomysqlConnectionPoolManager.get_pool(
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
                    self.logger.debug(
                        f"MySQL连接池初始化完成（表: {self.table_name}, 使用全局共享连接池）"
                    )
                except Exception as e:
                    self.logger.error(f"Aiomysql连接池初始化失败: {e}")
                    # 重置状态以便重试
                    self._pool_initialized = False
                    self.pool = None
                    raise

    # _execute_sql 和 _execute_batch_sql 方法继承自 BaseMySQLPipeline


