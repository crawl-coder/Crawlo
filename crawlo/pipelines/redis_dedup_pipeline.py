#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
基于 Redis 的数据项去重管道
========================
提供分布式环境下的数据项去重功能，防止保存重复的数据记录。

特点:
- 分布式支持: 多节点共享去重数据
- 高性能: 使用 Redis 集合进行快速查找
- 可配置: 支持自定义 Redis 连接参数
- 容错设计: 网络异常时不会丢失数据
"""
import redis
import hashlib
from typing import Optional

from crawlo import Item
from crawlo.spider import Spider
from crawlo.exceptions import DropItem, ItemDiscard
from crawlo.utils.log import get_logger


class RedisDedupPipeline:
    """基于 Redis 的数据项去重管道"""

    def __init__(
            self,
            redis_host: str = 'localhost',
            redis_port: int = 6379,
            redis_db: int = 0,
            redis_password: Optional[str] = None,
            redis_key: str = 'crawlo:item_fingerprints',
            log_level: str = "INFO"
    ):
        """
        初始化 Redis 去重管道
        
        :param redis_host: Redis 主机地址
        :param redis_port: Redis 端口
        :param redis_db: Redis 数据库编号
        :param redis_password: Redis 密码
        :param redis_key: 存储指纹的 Redis 键名
        :param log_level: 日志级别
        """
        self.logger = get_logger(self.__class__.__name__, log_level)
        
        # 初始化 Redis 连接
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            # Change INFO level log to DEBUG level to avoid redundant output
            # self.logger.debug(f"Redis connection successful: {redis_host}:{redis_port}/{redis_db}")  # 注释掉重复的日志
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            raise RuntimeError(f"Redis 连接失败: {e}")

        self.redis_key = redis_key
        self.dropped_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫配置创建管道实例"""
        settings = crawler.settings
        
        # 使用统一的Redis key命名规范: crawlo:{project_name}:item:fingerprint
        project_name = settings.get('PROJECT_NAME', 'default')
        redis_key = f"crawlo:{project_name}:item:fingerprint"
        
        return cls(
            redis_host=settings.get('REDIS_HOST', 'localhost'),
            redis_port=settings.get_int('REDIS_PORT', 6379),
            redis_db=settings.get_int('REDIS_DB', 0),
            redis_password=settings.get('REDIS_PASSWORD') or None,
            redis_key=redis_key,
            log_level=settings.get('LOG_LEVEL', 'INFO')
        )

    def process_item(self, item: Item, spider: Spider) -> Item:
        """
        处理数据项，进行去重检查
        
        :param item: 要处理的数据项
        :param spider: 爬虫实例
        :return: 处理后的数据项或抛出 DropItem 异常
        """
        try:
            # 生成数据项指纹
            fingerprint = self._generate_item_fingerprint(item)
            
            # 使用 Redis 的 SADD 命令检查并添加指纹
            # 如果指纹已存在，SADD 返回 0；如果指纹是新的，SADD 返回 1
            is_new = self.redis_client.sadd(self.redis_key, fingerprint)
            
            if not is_new:
                # 如果指纹已存在，丢弃这个数据项
                self.dropped_count += 1
                self.logger.info(f"Dropping duplicate item: {fingerprint}")
                raise ItemDiscard(f"Duplicate item: {fingerprint}")
            else:
                # 如果是新数据项，继续处理
                self.logger.debug(f"Processing new item: {fingerprint}")
                return item
                
        except redis.RedisError as e:
            self.logger.error(f"Redis error: {e}")
            # 在 Redis 错误时继续处理，避免丢失数据
            return item
        except ItemDiscard:
            # 重新抛出ItemDiscard异常，确保管道管理器能正确处理
            raise
        except Exception as e:
            self.logger.error(f"Error processing item: {e}")
            # 在其他错误时继续处理
            return item

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
        sorted_items = sorted(item_dict.items())
        
        # 生成指纹字符串
        fingerprint_string = '|'.join([f"{k}={v}" for k, v in sorted_items if v is not None])
        
        # 使用 SHA256 生成固定长度的指纹
        return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()

    def close_spider(self, spider: Spider) -> None:
        """
        爬虫关闭时的清理工作
        
        :param spider: 爬虫实例
        """
        try:
            # 获取去重统计信息
            total_items = self.redis_client.scard(self.redis_key)
            self.logger.info(f"Spider {spider.name} closed:")
            self.logger.info(f"  - Dropped duplicate items: {self.dropped_count}")
            self.logger.info(f"  - Fingerprints stored in Redis: {total_items}")
            
            # 注意：默认情况下不清理 Redis 中的指纹
            # 如果需要清理，可以在设置中配置
            if spider.crawler.settings.getbool('REDIS_DEDUP_CLEANUP', False):
                deleted = self.redis_client.delete(self.redis_key)
                self.logger.info(f"  - Cleaned fingerprints: {deleted}")
        except Exception as e:
            self.logger.error(f"Error closing spider: {e}")