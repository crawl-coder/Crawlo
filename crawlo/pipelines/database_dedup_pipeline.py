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
import hashlib
import aiomysql

from crawlo import Item
from crawlo.exceptions import DropItem, ItemDiscard
from crawlo.spider import Spider
from crawlo.utils.log import get_logger


class DatabaseDedupPipeline:
    """基于数据库的数据项去重管道"""

    def __init__(
            self,
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
        
        :param db_host: 数据库主机地址
        :param db_port: 数据库端口
        :param db_user: 数据库用户名
        :param db_password: 数据库密码
        :param db_name: 数据库名称
        :param table_name: 存储指纹的表名
        :param log_level: 日志级别
        """
        self.logger = get_logger(self.__class__.__name__, log_level)
        
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
        self.dropped_count = 0
        self.connection = None
        self.pool = None

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        return cls(
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

    async def process_item(self, item: Item, spider: Spider) -> Item:
        """
        处理数据项，进行去重检查
        
        :param item: 要处理的数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        try:
            # 生成数据项指纹
            fingerprint = self._generate_item_fingerprint(item)
            
            # 检查指纹是否已存在
            exists = await self._check_fingerprint_exists(fingerprint)
            
            if exists:
                # 如果已存在，丢弃这个数据项
                self.dropped_count += 1
                self.logger.debug(f"Dropping duplicate item: {fingerprint[:20]}...")
                raise ItemDiscard(f"Duplicate item: {fingerprint}")
            else:
                # 记录新数据项的指纹
                await self._insert_fingerprint(fingerprint)
                self.logger.debug(f"Processing new item: {fingerprint[:20]}...")
                return item
                
        except Exception as e:
            self.logger.error(f"Error processing item: {e}")
            # 在错误时继续处理，避免丢失数据
            return item

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

    async def _insert_fingerprint(self, fingerprint: str) -> None:
        """
        插入新指纹
        
        :param fingerprint: 数据项指纹
        """
        insert_sql = f"INSERT INTO `{self.table_name}` (`fingerprint`) VALUES (%s)"
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute(insert_sql, (fingerprint,))
                    await conn.commit()
                except aiomysql.IntegrityError:
                    # 指纹已存在（并发情况下可能发生）
                    await conn.rollback()
                    raise ItemDiscard(f"重复的数据项: {fingerprint}")
                except Exception:
                    await conn.rollback()
                    raise

    def _generate_item_fingerprint(self, item: Item) -> str:
        """
        生成数据项指纹
        
        基于数据项的所有字段生成唯一指纹，用于去重判断。
        
        :param item: 数据项
        :return: 指纹字符串
        """
        # 将数据项转换为可序列化的字典
        try:
            item_dict = item.to_dict()
        except AttributeError:
            # 兼容没有to_dict方法的Item实现
            item_dict = dict(item)
        
        # 对字典进行排序以确保一致性