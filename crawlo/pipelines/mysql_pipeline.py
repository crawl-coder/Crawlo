# -*- coding: utf-8 -*-
import re
import asyncio
import async_timeout
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

from crawlo.items import Item
from crawlo.logging import get_logger
from crawlo.exceptions import ItemDiscard
from crawlo.utils.db.sql_builder import SQLBuilder
from crawlo.utils.resource_manager import ResourceType
from crawlo.utils.db.mysql_helper import MySQLHelper
from crawlo.utils.db.mysql_connection_pool import (
    MySQLConnectionPoolManager,
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

        # 初始化配置
        self._init_config()
        
        # 记录管道初始化完成（合并配置信息）
        self.logger.info(
            f"MySQL Pipeline initialized - "
            f"host={self.settings.get('MYSQL_HOST', 'localhost')}:{self.settings.get('MYSQL_PORT', 3306)}, "
            f"database={self.settings.get('MYSQL_DB', 'crawlo_db')}, "
            f"table={self.table_name}, "
            f"batch_size={self.batch_size}, "
            f"batch_mode={'enabled' if self.use_batch else 'disabled'}, "
            f"pool_size={self.settings.get('MYSQL_POOL_MIN_SIZE', 2)}-{self.settings.get('MYSQL_POOL_MAX_SIZE', 30)}"
        )

        # 使用异步锁和初始化标志确保线程安全
        self._pool_lock = asyncio.Lock()
        self._pool_initialized = False
        self.pool = None
        
        # 批量插入相关
        self.batch_buffer: List[Dict] = []  # 批量缓冲区
        
        # 新增配置项
        self.batch_timeout = self.settings.get_int('MYSQL_BATCH_TIMEOUT', 120)  # 批量操作超时时间，默认120秒
        
        # 配置项说明:
        # MYSQL_BATCH_SIZE: 批量插入的大小，默认100
        # MYSQL_USE_BATCH: 是否启用批量插入，默认False
        # MYSQL_EXECUTE_MAX_RETRIES: SQL执行最大重试次数，默认3
        # MYSQL_EXECUTE_TIMEOUT: SQL执行超时时间（秒），默认60
        # MYSQL_EXECUTE_RETRY_DELAY: 重试之间的延迟系数，默认0.2
        # MYSQL_BATCH_TIMEOUT: 批量操作超时时间（秒），默认120
        
        # MySQLHelper 实例（用于数据库操作）
        self._mysql_helper: Optional[MySQLHelper] = None
            
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
        
        # 检查表存在配置：默认为True，设为False可跳过表存在性检查
        self.check_table_exists = self.settings.get_bool('MYSQL_CHECK_TABLE_EXISTS', True)
        
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
            ('MYSQL_DB', self.settings.get('MYSQL_DB', 'crawlo_db')),
            ('MYSQL_USER', self.settings.get('MYSQL_USER', 'root')),
        ]
        
        for config_name, config_value in required_configs:
            if not config_value:
                self.logger.error(f"缺少必需的配置项: {config_name}")
                return False
        
        return True
    
    @staticmethod
    def _is_pool_active(pool):
        """检查连接池是否活跃
        
        Args:
            pool: 数据库连接池对象
            
        Returns:
            bool: 连接池是否活跃
        """
        return is_pool_active(pool)
                
    @staticmethod
    def _is_conn_active(conn):
        """检查连接是否活跃"""
        if not conn:
            return False
        
        # 使用 _closed 属性检查连接状态
        if hasattr(conn, '_closed'):
            return not conn._closed
        
        # 没有明确的关闭状态属性，假设连接有效
        return True
    
    async def _insert_with_helper(self, item_dict: Dict, prefer_alias: bool = True, **kwargs) -> int:
        """
        使用 MySQLHelper 插入数据
        
        Args:
            item_dict: 数据字典
            prefer_alias: 是否优先使用别名语法（已废弃参数，保留以兼容接口）
            
        Returns:
            int: 影响的行数
        """
        # 使用 MySQLHelper 插入数据
        rowcount = await self._mysql_helper.insert(
            table=self.table_name,
            data=item_dict,
            auto_update=self.auto_update,
            update_columns=self.update_columns,
            insert_ignore=self.insert_ignore
        )
        return rowcount
    
    async def _batch_insert_with_helper(self, datas: List[Dict]) -> int:
        """
        使用 MySQLHelper 批量插入数据
        
        Args:
            datas: 数据字典列表
            
        Returns:
            int: 影响的行数
        """
        rowcount = await self._mysql_helper.insert_many(
            table=self.table_name,
            datas=datas,
            auto_update=self.auto_update,
            update_columns=self.update_columns,
            insert_ignore=self.insert_ignore,
            batch_size=len(datas)
        )
        return rowcount
    
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
            # 单条插入逻辑 - 使用 MySQLHelper
            try:
                # 确保 MySQLHelper 已初始化
                await self._ensure_initialized()
                
                item_dict = dict(item)
                rowcount = await self._insert_with_helper(item_dict, prefer_alias=True, **kwargs)
                if rowcount > 1:
                    self.logger.debug(
                        f"成功插入 {rowcount} 条记录到表 {self.table_name}"
                    )
                elif rowcount == 1:
                    self.logger.debug(f"成功插入单条记录到表 {self.table_name}")
                else:
                    # 当使用 MYSQL_UPDATE_COLUMNS 时，如果更新的字段值与现有记录相同，
                    # MySQL 不会实际更新任何数据，rowcount 会是 0
                    if self.update_columns:
                        self.logger.debug(f"数据已存在，{self.update_columns}字段未发生变化，无需更新")
                    else:
                        # 优化：将单条插入的重复数据警告改为 DEBUG 级别
                        self.logger.debug("SQL 执行成功但未插入新记录（重复数据）")
    
                # 统计计数移到这里，与AiomysqlMySQLPipeline保持一致
                self.crawler.stats.inc_value('mysql/insert_success')
                self.crawler.stats.inc_value('mysql/rows_requested', 1)
                self.crawler.stats.inc_value('mysql/rows_affected', rowcount or 0)
                if self.insert_ignore and not self.update_columns and (rowcount or 0) == 0:
                    self.crawler.stats.inc_value('mysql/rows_ignored_by_duplicate', 1)
                return item
    
            except Exception as e:
                # 添加更多调试信息
                error_msg = f"处理失败：{str(e)}"
                err_str = str(e).lower()
                
                # 如果是重复键错误，直接丢弃，不要重试
                if "duplicate entry" in err_str or "1062" in err_str:
                    self.logger.debug(f"数据已存在，跳过：{item.get('pmid', 'unknown')}")
                    self.crawler.stats.inc_value('mysql/rows_ignored_by_duplicate', 1)
                    return item  # 直接返回成功，不抛出异常
                
                # 如果是锁等待超时，立即放弃，避免卡住
                if "lock wait timeout" in err_str or "1205" in err_str:
                    self.logger.warning(f"锁等待超时，跳过本次操作")
                    self.crawler.stats.inc_value('mysql/lock_timeout_count', 1)
                    return item  # 直接返回成功，不抛出异常
                
                self.logger.error(f"处理数据项时发生错误：{error_msg}")
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
                
                self.logger.debug(f"尝试获取数据库连接 (尝试 {attempt+1}/{max_retries})")
                                
                # 检查连接池是否活跃
                if not self._is_pool_active(self.pool):
                    self.logger.warning("连接池已关闭，尝试重新初始化")
                    # 尝试重新初始化连接池
                    self._pool_initialized = False
                    await self._ensure_pool()
                    if not self.pool or not self._is_pool_active(self.pool):
                        raise RuntimeError("Failed to reinitialize database connection pool")

                async with async_timeout.timeout(timeout):
                    self.logger.debug("正在获取连接...")
                    conn = await self.pool.acquire()
                    self.logger.debug("成功获取数据库连接")
                
                # 检查连接是否仍然活跃
                if not self._is_conn_active(conn):
                    self.logger.warning("获取的连接已失效，将重新尝试")
                    if conn:
                        await self.pool.release(conn)
                    continue # 重试
                
                # 执行SQL并处理事务
                self.logger.debug("开始执行SQL事务...")
                rowcount = await self._execute_sql_with_transaction(conn, sql, values)
                self.logger.debug(f"SQL执行完成，影响行数: {rowcount}")
                
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
                    self.logger.debug("正在释放连接...")
                    await self.pool.release(conn)
                    self.logger.debug("连接已释放")
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

    async def _flush_batch(self, spider_name: str, is_cleanup: bool = False):
        """刷新批量缓冲区并执行批量插入 - 使用 MySQLHelper
        
        Args:
            spider_name: 爬虫名称
            is_cleanup: 是否为清理模式（是则合并日志输出）
        """
        # 确保资源已初始化
        await self._ensure_initialized()
        
        # 快照当前批量，避免在 await 过程中 buffer 被其他协程修改
        async with self._pool_lock:
            if not self.batch_buffer:
                self.logger.debug("批量缓冲区为空，跳过刷新")
                return
                
            # 使用切片复制，避免引用同一对象；不立即清空，失败时可重试
            current_batch = self.batch_buffer[:]
            processed_count = len(current_batch)
            # 立即清空缓冲区，避免重复处理
            self.batch_buffer.clear()
        
        if not current_batch:  # 双重检查
            self.logger.debug("批次数据为空，跳过")
            return
        
        try:
            # 使用 MySQLHelper 进行批量插入
            rowcount = await self._batch_insert_with_helper(current_batch)
                
            if rowcount > 0:
                # 成功日志：包含关键信息
                self.logger.info(
                    f"批量插入成功：{processed_count} 条记录到表 {self.table_name}，实际影响 {rowcount} 行"
                )
            else:
                # 当使用 MYSQL_UPDATE_COLUMNS 时，如果更新的字段值与现有记录相同，
                # MySQL 不会实际更新任何数据，rowcount 会是 0
                if self.update_columns:
                    self.logger.debug(f"批量数据已存在，{self.update_columns}字段未发生变化，无需更新")
                else:
                    self.logger.debug("批量 SQL 执行完成但未插入新记录（全部为重复数据）")

            self.crawler.stats.inc_value('mysql/batch_insert_success')
            self.crawler.stats.inc_value('mysql/rows_requested', processed_count)
            self.crawler.stats.inc_value('mysql/rows_affected', rowcount or 0)
            if self.insert_ignore and not self.update_columns and (rowcount or 0) < processed_count:
                ignored_count = processed_count - (rowcount or 0)
                self.crawler.stats.inc_value('mysql/rows_ignored_by_duplicate', ignored_count)
                if ignored_count >= processed_count * 0.5:
                    self.logger.info(
                        f"批量处理 {processed_count} 条记录，其中 {ignored_count} 条为重复数据（重复率：{ignored_count/processed_count*100:.1f}%）"
                    )

        except Exception as e:
            # 批量插入失败时，尝试降级为单条插入以挽救数据
            self.logger.warning(f"批量执行失败，尝试降级为单条插入: {e}")
            try:
                rowcount = await self._execute_batch_as_individual(current_batch)
                self.crawler.stats.inc_value('mysql/batch_insert_success')
                self.crawler.stats.inc_value('mysql/rows_requested', processed_count)
                self.crawler.stats.inc_value('mysql/rows_affected', rowcount or 0)
            except Exception as individual_err:
                error_msg = f"批量插入失败: {str(e)}, 降级单条插入也失败: {str(individual_err)}"
                self.logger.error(f"批量处理数据时发生错误: {error_msg}")
                self.crawler.stats.inc_value('mysql/batch_insert_failed')
                # 失败时将数据重新放回缓冲区，以便重试
                async with self._pool_lock:
                    self.batch_buffer.extend(current_batch)
                raise ItemDiscard(error_msg)
    
    async def _execute_batch_as_individual(self, datas: List[Dict]) -> int:
        """将批量数据降级为单条执行，以挽救数据 - 使用 MySQLHelper"""
        total_rows = 0
        failed_count = 0
        
        for i, data in enumerate(datas):
            try:
                # 使用 MySQLHelper 插入单条数据
                rowcount = await self._mysql_helper.insert(
                    table=self.table_name,
                    data=data,
                    auto_update=self.auto_update,
                    update_columns=self.update_columns,
                    insert_ignore=self.insert_ignore
                )
                total_rows += rowcount or 0
            except Exception as row_err:
                failed_count += 1
                self.logger.error(f"单条插入也失败 (第{i+1}/{len(datas)}条): {row_err}")
                
        self.logger.info(f"降级执行完成: 成功 {len(datas)-failed_count} 条, 失败 {failed_count} 条, 影响 {total_rows} 行")
        return total_rows

    async def _check_table_exists(self):
        """检查数据表是否存在"""
        if not self.pool:
            return False
            
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查表是否存在的SQL
                    check_table_sql = f"""
                    SELECT COUNT(*) as count FROM information_schema.tables 
                    WHERE table_schema = DATABASE() AND table_name = '{self.table_name}'
                    """
                    await cursor.execute(check_table_sql)
                    result = await cursor.fetchone()
                    
                    # 兼容不同驱动返回的格式，可能是字典也可能是元组
                    if result:
                        if isinstance(result, dict):
                            # 字典格式：{'count': 1}
                            exists = result.get('count', 0) > 0
                        elif isinstance(result, (tuple, list)):
                            # 元组格式：(1,) - 对于SELECT COUNT(*)，第一列是计数值
                            exists = result[0] > 0 if len(result) > 0 else False
                        else:
                            # 其他格式，尝试直接转换为布尔值
                            exists = bool(result)
                    else:
                        exists = False
                        
                    if exists:
                        self.logger.debug(f"表 {self.table_name} 存在")
                    else:
                        self.logger.warning(f"表 {self.table_name} 不存在")
                        
                    return exists
            
        except Exception as e:
            self.logger.error(f"检查表 {self.table_name} 存在性时出错: {e}")
            return False
    
    async def _initialize_resources(self):
        """初始化连接池资源并注册到资源管理器"""
        # 确保连接池已初始化
        await self._ensure_pool()
        self.logger.debug("连接池初始化完成")
        
        # 初始化 MySQLHelper（复用连接池）
        self._mysql_helper = await MySQLHelper.get_instance(self.settings)
        self.logger.debug("MySQLHelper 初始化完成")
            
        # 根据配置决定是否检查表是否存在
        if self.check_table_exists:
            self.logger.debug("开始检查表是否存在...")
            await self._check_table_exists()
            self.logger.debug("表存在性检查完成")
                
        # 将连接池注册到资源管理器，以便在爬虫关闭时自动清理
        if self.pool:
            self.logger.debug(f"将{'asyncmy'}连接池注册到资源管理器")
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                resource_type=ResourceType.PIPELINE,  # 使用 PIPELINE 类型表示数据库连接池
                name=f"mysql_{'asyncmy'}_pool"
            )
                
        # 调用父类的初始化方法
        await super()._initialize_resources()
        self.logger.debug("MySQL 管道资源初始化完成")
        
    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            if pool:
                pool.close()
                await pool.wait_closed()
                self.logger.info(f"{'asyncmy'} MySQL连接池已关闭")
        except Exception as e:
            self.logger.error(f"关闭{'asyncmy'} MySQL连接池时发生错误: {e}")
        
    async def _cleanup_resources(self):
        """清理资源"""
        self.logger.debug("开始清理 MySQL 管道资源...")
        
        # 在关闭前强制刷新剩余的批量数据（清理阶段的日志由 _flush_batch 统一输出）
        if self.use_batch and self.batch_buffer:
            spider_name = getattr(self.crawler.spider, 'name', 'unknown')
            await self._flush_batch(spider_name, is_cleanup=True)
        
        # 清空批量缓冲区
        self.batch_buffer.clear()
        self.logger.debug("批量缓冲区已清空")
        
        # 无论是否为调度任务，都需要重置初始化标志，确保下次执行时能正确重新初始化连接池
        # 即使在调度模式下，每轮任务结束后也需要清理所有资源，包括连接池
        self.logger.debug("重置连接池初始化标志，确保下次执行时重新初始化")
        self._pool_initialized = False
        
        # 调用父类的清理方法
        await super()._cleanup_resources()
        self.logger.debug("MySQL pipeline resources cleanup completed")
        
    
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
            
        # 处理 1205 错误：锁等待超时，立即放弃，不要重试
        if "lock wait timeout" in err_str or "1205" in err_str:
            self.logger.warning(f"检测到锁等待超时，跳过本次操作：{err_str}")
            if conn:
                await self._close_conn_properly(conn)
            return False  # 不需要重试，直接失败
            
        # 处理 2014 错误：如果报错同步问题，强制销毁连接
        if "2014" in err_str or "command out of sync" in err_str:
            self.logger.warning(f"检测到脏连接 (2014)，正在丢弃并重试：{err_str}")
            if conn:
                await self._close_conn_properly(conn)
                conn = None # 标记为 None，防止在 finally 中再次 release
            return True  # 需要重试
    
        # 其他常见重试逻辑（死锁、断连等）
        if (("deadlock found" in err_str or "2006" in err_str or 
             "2013" in err_str or "lost connection" in err_str) and 
            attempt < max_retries - 1):
            await asyncio.sleep(self.execute_retry_delay * (attempt + 1))
            return True  # 需要重试
        
        # 不需要重试，返回False
        return False



class MySQLPipeline(BaseMySQLPipeline):
    """使用asyncmy库的MySQL管道实现"""
    
    def __init__(self, crawler):
        super().__init__(crawler)

    @classmethod
    async def from_crawler(cls, crawler):
        """创建管道实例（每次调用创建新实例，连接池由管理器统一复用）"""
        return cls(crawler)

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
                    self.pool = await MySQLConnectionPoolManager.get_pool(
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


    

