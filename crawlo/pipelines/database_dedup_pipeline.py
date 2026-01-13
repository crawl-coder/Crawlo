#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于数据库的数据项去重管道
=======================
提供持久化去重功能，适用于需要长期运行或断点续爬的场景。

特点:
- 持久化存储: 重启爬虫后仍能保持去重状态
- 可靠性高: 数据库事务保证一致性
- 适用性广: 支持多种数据库后端
- 可扩展: 支持自定义表结构和字段
"""
import aiomysql

from crawlo.logging import get_logger
from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.spider import Spider


class DatabaseDedupPipeline(DedupPipeline):
    """基于数据库的数据项去重管道"""

    def __init__(
            self,
            crawler,
            db_host: str = 'localhost',
            db_port: int = 3306,
            db_user: str = 'root',
            db_password: str = '',
            db_name: str = 'crawlo',
            table_name: str = 'item_fingerprints',
            log_level: str = "INFO"
    ):
        """
        初始化数据库去重管道
        
        :param crawler: Crawler实例
        :param db_host: 数据库主机地址
        :param db_port: 数据库端口
        :param db_user: 数据库用户名
        :param db_password: 数据库密码
        :param db_name: 数据库名称
        :param table_name: 存储指纹的表名
        :param log_level: 日志级别
        """
        super().__init__(crawler)
        
        self.logger = get_logger(self.__class__.__name__)
        
        # 数据库连接参数
        self.db_config = {
            'host': db_host,
            'port': db_port,
            'user': db_user,
            'password': db_password,
            'db': db_name,
            'autocommit': False
        }
        
        self.table_name = table_name
        self.connection = None
        self.pool = None

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        return cls(
            crawler=crawler,
            db_host=settings.get('DB_HOST', 'localhost'),
            db_port=settings.getint('DB_PORT', 3306),
            db_user=settings.get('DB_USER', 'root'),
            db_password=settings.get('DB_PASSWORD', ''),
            db_name=settings.get('DB_NAME', 'crawlo'),
            table_name=settings.get('DB_DEDUP_TABLE', 'item_fingerprints'),
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    async def open_spider(self, spider: Spider) -> None:
        """
        爬虫启动时初始化数据库连接
        
        :param spider: 爬虫实例
        """
        try:
            # 创建连接池
            self.pool = await aiomysql.create_pool(
                **self.db_config,
                minsize=2,
                maxsize=10
            )
            
            # 创建去重表（如果不存在）
            await self._create_dedup_table()
            
            self.logger.info(f"Database deduplication pipeline initialized: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['db']}.{self.table_name}")
        except Exception as e:
            self.logger.error(f"Database deduplication pipeline initialization failed: {e}")
            raise RuntimeError(f"数据库去重管道初始化失败: {e}")

    async def _create_dedup_table(self) -> None:
        """创建去重表"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `fingerprint` VARCHAR(64) NOT NULL UNIQUE,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_fingerprint` (`fingerprint`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(create_table_sql)
                await conn.commit()

    async def _initialize_resources(self):
        """初始化资源"""
        # 数据库连接已在open_spider中创建，这里注册到资源管理器
        if self.pool:
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                name="db_pool"
            )
        # 调用父类的初始化方法
        await super()._initialize_resources()

    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            pool.close()
            await pool.wait_closed()
            self.logger.info("Database pool closed")
        except Exception as e:
            self.logger.error(f"Error closing database pool: {e}")

    async def _cleanup_resources(self):
        """清理资源"""
        # 调用父类的清理方法
        await super()._cleanup_resources()

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        """
        检查指纹是否已存在
        
        :param fingerprint: 数据项指纹
        :return: 是否存在
        """
        check_sql = f"SELECT 1 FROM `{self.table_name}` WHERE `fingerprint` = %s LIMIT 1"
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(check_sql, (fingerprint,))
                result = await cursor.fetchone()
                return result is not None

    async def _record_fingerprint(self, fingerprint: str) -> None:
        """
        记录指纹
        
        :param fingerprint: 数据项指纹
        """
        insert_sql = f"INSERT IGNORE INTO `{self.table_name}` (`fingerprint`) VALUES (%s)"
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute(insert_sql, (fingerprint,))
                    await conn.commit()
                    self.crawler.stats.inc_value('dedup/db_insert_success')
                except Exception as e:
                    await conn.rollback()
                    self.logger.error(f"Error recording fingerprint: {e}")
                    self.crawler.stats.inc_value('dedup/db_insert_error')
                    raise