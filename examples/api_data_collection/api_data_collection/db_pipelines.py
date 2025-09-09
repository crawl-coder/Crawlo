# -*- coding: UTF-8 -*-
"""
api_data_collection.db_pipelines
============================
基于数据库的去重数据处理管道
"""

import hashlib
import aiomysql
from crawlo.exceptions import DropItem


class DatabaseDeduplicationPipeline:
    """基于数据库的去重管道"""
    
    def __init__(self, host, port, user, password, database, table):
        """
        初始化数据库连接参数
        :param host: 数据库主机
        :param port: 数据库端口
        :param user: 数据库用户
        :param password: 数据库密码
        :param database: 数据库名
        :param table: 表名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.table = table
        self.pool = None
    
    @classmethod
    def from_settings(cls, settings):
        """
        从设置中创建管道实例
        :param settings: 设置对象
        :return: 管道实例
        """
        return cls(
            host=settings.get('MYSQL_HOST', 'localhost'),
            port=settings.get('MYSQL_PORT', 3306),
            user=settings.get('MYSQL_USER', 'root'),
            password=settings.get('MYSQL_PASSWORD', ''),
            database=settings.get('MYSQL_DB', 'api_data_collection'),
            table=settings.get('MYSQL_TABLE', 'crawled_data')
        )
    
    async def open_spider(self, spider):
        """
        爬虫启动时的初始化工作
        :param spider: 爬虫实例
        """
        # 创建数据库连接池
        self.pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            charset='utf8mb4',
            autocommit=True
        )
        
        # 确保去重表存在
        await self._create_dedup_table()
    
    async def _create_dedup_table(self):
        """创建去重表"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 创建用于存储指纹的表
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS `{self.table}_fingerprints` (
                    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    `fingerprint` VARCHAR(64) NOT NULL UNIQUE,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX `idx_fingerprint` (`fingerprint`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                await cursor.execute(create_table_sql)
    
    async def process_item(self, item, spider):
        """
        处理数据项，进行去重检查
        :param item: 数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        # 基于关键字段生成数据项指纹
        fingerprint = self._generate_item_fingerprint(item)
        
        # 检查指纹是否已存在
        exists = await self._check_fingerprint_exists(fingerprint)
        
        if exists:
            # 如果已存在，丢弃这个数据项
            raise DropItem(f"重复的数据项: {fingerprint}")
        else:
            # 记录新指纹
            await self._insert_fingerprint(fingerprint)
            return item
    
    async def _check_fingerprint_exists(self, fingerprint):
        """
        检查指纹是否已存在
        :param fingerprint: 指纹
        :return: 是否存在
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                check_sql = f"SELECT 1 FROM `{self.table}_fingerprints` WHERE `fingerprint` = %s LIMIT 1"
                await cursor.execute(check_sql, (fingerprint,))
                result = await cursor.fetchone()
                return result is not None
    
    async def _insert_fingerprint(self, fingerprint):
        """
        插入新指纹
        :param fingerprint: 指纹
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                insert_sql = f"INSERT IGNORE INTO `{self.table}_fingerprints` (`fingerprint`) VALUES (%s)"
                await cursor.execute(insert_sql, (fingerprint,))
    
    def _generate_item_fingerprint(self, item):
        """
        生成数据项指纹
        :param item: 数据项
        :return: 指纹字符串
        """
        # 使用数据项的关键字段生成指纹
        key_fields = [
            str(item.get('id', '')),
            item.get('name', ''),
            item.get('category', '')
        ]
        fingerprint_string = '|'.join(key_fields)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    async def close_spider(self, spider):
        """
        爬虫关闭时的清理工作
        :param spider: 爬虫实例
        """
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()