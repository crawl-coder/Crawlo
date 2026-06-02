#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于 MySQL 的数据项去重管道
=========================
提供持久化去重功能，适用于需要长期运行或断点续爬的场景。
"""

import asyncmy

from crawlo.pipelines.base_pipeline import DedupPipeline
from crawlo.spider import Spider


class MySQLDedupPipeline(DedupPipeline):
    """基于 MySQL 的数据项去重管道"""

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
        super().__init__(crawler)
        
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
        """爬虫启动时初始化数据库连接"""
        try:
            self.pool = await asyncmy.create_pool(
                **self.db_config,
                minsize=2,
                maxsize=10
            )
            await self._create_dedup_table()
            self.logger.info(
                f"MySQLDedupPipeline initialized: "
                f"{self.db_config['host']}:{self.db_config['port']}/"
                f"{self.db_config['db']}.{self.table_name}"
            )
        except Exception as e:
            self.logger.error(f"MySQLDedupPipeline init failed: {e}")
            raise RuntimeError(f"数据库去重管道初始化失败: {e}")

    async def _create_dedup_table(self) -> None:
        """创建去重表（UNIQUE 已自带索引，无需额外 idx_fingerprint）"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `fingerprint` VARCHAR(64) NOT NULL UNIQUE,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(create_table_sql)
                await conn.commit()

    async def _initialize_resources(self):
        """初始化资源"""
        if self.pool:
            self.register_resource(
                resource=self.pool,
                cleanup_func=self._close_pool,
                name="db_pool"
            )
        await super()._initialize_resources()

    async def _close_pool(self, pool):
        """关闭连接池"""
        try:
            pool.close()
            await pool.wait_closed()
            self.logger.info("Database pool closed")
        except Exception as e:
            self.logger.error(f"Error closing database pool: {e}")

    # _cleanup_resources: 无需重写，直接继承 DedupPipeline 默认实现

    async def _check_fingerprint_exists(self, fingerprint: str) -> bool:
        check_sql = f"SELECT 1 FROM `{self.table_name}` WHERE `fingerprint` = %s LIMIT 1"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(check_sql, (fingerprint,))
                result = await cursor.fetchone()
                return result is not None

    async def _record_fingerprint(self, fingerprint: str) -> None:
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


# 向后兼容别名
DatabaseDedupPipeline = MySQLDedupPipeline
